"""
Dataset Management, Bootstrapping, and Fine-Tuning Preparation for DEE
Spec Reference: HYC-SCO-2026-3841 (§12.1-§12.4, §12.3 Continuous Learning Loop)

Supports:
  1. Drop-in raw document dataset loading (PDF, PNG, JPG, JPEG, TIFF, BMP).
  2. Matching raw documents with ground truth labels (JSON / JSONL / sidecar files).
  3. Multilingual dataset splitting (Train / Val / Test).
  4. Pseudo-labeling / Bootstrapping unannotated raw images via DEE pipeline.
  5. Exporting instruction fine-tuning datasets (Claude/OpenAI JSONL format) for model retraining.
  6. Exporting few-shot exemplar banks indexed by language and document type.
"""

from __future__ import annotations
import os
import re
import json
import uuid
import random
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

from pipelines.dee.models import (
    DocumentType,
    ExtractedEntitiesJson,
    DeeExtractionResult,
)
from pipelines.dee.ocr import dee_ocr
from pipelines.dee.prompts import get_prompt_for_document_type


SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}
SUPPORTED_DOC_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf", ".txt"}


class DeeDatasetItem(BaseModel):
    """
    Individual sample item inside an image/document dataset.
    """
    item_id: str
    file_path: str
    file_name: str
    mime_type: str
    document_type: DocumentType = DocumentType.SALE_DEED
    language: Optional[str] = None
    ground_truth: Optional[ExtractedEntitiesJson] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeeDatasetManager:
    """
    Orchestrates dataset discovery, bootstrapping, and fine-tuning exports.
    """

    def __init__(self, ocr_processor=None):
        self.ocr = ocr_processor or dee_ocr

    def discover_documents(self, data_dir: str | Path) -> List[Path]:
        """
        Recursively discovers all image and PDF documents in the target folder.
        """
        data_path = Path(data_dir)
        if not data_path.exists():
            return []

        doc_paths: List[Path] = []
        for ext in SUPPORTED_DOC_EXTENSIONS:
            doc_paths.extend(data_path.rglob(f"*{ext}"))
            doc_paths.extend(data_path.rglob(f"*{ext.upper()}"))
        return sorted(list(set(doc_paths)))

    def infer_mime_type(self, file_path: Path | str) -> str:
        """Infers MIME type from file extension."""
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return "application/pdf"
        elif ext in (".png",):
            return "image/png"
        elif ext in (".jpg", ".jpeg"):
            return "image/jpeg"
        elif ext in (".tif", ".tiff"):
            return "image/tiff"
        elif ext in (".bmp",):
            return "image/bmp"
        elif ext in (".webp",):
            return "image/webp"
        elif ext in (".txt",):
            return "text/plain"
        return "application/octet-stream"

    def load_dataset(
        self,
        data_dir: str | Path,
        annotations_file: Optional[str | Path] = None,
    ) -> List[DeeDatasetItem]:
        """
        Loads dataset items by pairing discovered documents with annotations.
        Supports:
          - Single master annotations JSON (`annotations.json` or `ground_truth.json`).
          - JSONL labels file (`labels.jsonl`).
          - Sidecar JSON file per document (`<document_stem>.json`).
        """
        doc_paths = self.discover_documents(data_dir)
        data_path = Path(data_dir)

        # 1. Look for master annotations file
        annotations_map: Dict[str, Any] = {}
        target_ann_file = None

        if annotations_file:
            target_ann_file = Path(annotations_file)
        else:
            candidates = [
                data_path / "ground_truth.json",
                data_path / "annotations.json",
                data_path / "labels.json",
                data_path / "labels.jsonl",
            ]
            for c in candidates:
                if c.exists():
                    target_ann_file = c
                    break

        if target_ann_file and target_ann_file.exists():
            if target_ann_file.suffix == ".jsonl":
                with open(target_ann_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            key = entry.get("file_name") or entry.get("item_id")
                            if key:
                                annotations_map[key] = entry
            else:
                with open(target_ann_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        annotations_map = data
                    elif isinstance(data, list):
                        for entry in data:
                            key = entry.get("file_name") or entry.get("item_id")
                            if key:
                                annotations_map[key] = entry

        # 2. Build dataset items
        items: List[DeeDatasetItem] = []
        for p in doc_paths:
            file_name = p.name
            file_stem = p.stem
            mime = self.infer_mime_type(p)

            # Match annotation
            ann = annotations_map.get(file_name) or annotations_map.get(file_stem)

            # Check sidecar JSON if not found in master
            if not ann:
                sidecar = p.with_suffix(".json")
                if sidecar.exists():
                    try:
                        with open(sidecar, "r", encoding="utf-8") as sf:
                            ann = json.load(sf)
                    except Exception:
                        pass

            # Resolve document type
            doc_type = DocumentType.SALE_DEED
            gt_entities = None
            detected_lang = None

            if ann:
                dt_str = ann.get("document_type") or ann.get("documentType")
                if dt_str:
                    try:
                        doc_type = DocumentType(dt_str)
                    except ValueError:
                        pass

                gt_raw = ann.get("ground_truth") or ann.get("entities") or ann
                if isinstance(gt_raw, dict) and ("owners" in gt_raw or "survey_number" in gt_raw):
                    try:
                        gt_entities = ExtractedEntitiesJson(**gt_raw)
                    except Exception:
                        pass

                detected_lang = ann.get("language") or (gt_entities.regional_language if gt_entities else None)

            item = DeeDatasetItem(
                item_id=f"item_{file_stem}",
                file_path=str(p.resolve()),
                file_name=file_name,
                mime_type=mime,
                document_type=doc_type,
                language=detected_lang,
                ground_truth=gt_entities,
                metadata={"source_dir": str(data_path)},
            )
            items.append(item)

        return items

    def split_dataset(
        self,
        items: List[DeeDatasetItem],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> Tuple[List[DeeDatasetItem], List[DeeDatasetItem], List[DeeDatasetItem]]:
        """
        Splits dataset into deterministic Train / Validation / Test sets.
        """
        shuffled = list(items)
        random.seed(seed)
        random.shuffle(shuffled)

        n = len(shuffled)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_items = shuffled[:n_train]
        val_items = shuffled[n_train:n_train + n_val]
        test_items = shuffled[n_train + n_val:]

        return train_items, val_items, test_items

    def bootstrap_unlabeled_dataset(
        self,
        data_dir: str | Path,
        output_annotations_file: str | Path,
        pipeline=None,
    ) -> Dict[str, Any]:
        """
        Runs DEE on unannotated dumped raw images, generating structured pseudo-labels
        with confidence flags (auto-approved vs manual ops review needed).
        """
        from pipelines.dee.pipeline import dee_pipeline
        active_pipeline = pipeline or dee_pipeline

        items = self.load_dataset(data_dir)
        results = []
        auto_approved_count = 0
        manual_review_count = 0

        for item in items:
            with open(item.file_path, "rb") as f:
                content = f.read()

            res: DeeExtractionResult = active_pipeline.process_document(
                file_input=content,
                document_type=item.document_type,
                document_id=item.item_id,
                property_id=f"prop-{item.item_id}",
                mime_type=item.mime_type,
            )

            is_auto = not res.requiresManualReview
            if is_auto:
                auto_approved_count += 1
            else:
                manual_review_count += 1

            entry = {
                "file_name": item.file_name,
                "item_id": item.item_id,
                "document_type": item.document_type.value,
                "status": res.status.value,
                "requires_manual_review": res.requiresManualReview,
                "confidence_score": res.aiConfidenceScore,
                "language": res.aiExtractedDataJson.regional_language or "English",
                "ground_truth": res.aiExtractedDataJson.model_dump(mode="json"),
                "suggested_resolution": res.aiExtractedDataJson.suggested_resolution,
            }
            results.append(entry)

        out_path = Path(output_annotations_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return {
            "total_documents": len(items),
            "auto_approved_count": auto_approved_count,
            "manual_review_count": manual_review_count,
            "auto_approval_rate": round(auto_approved_count / max(1, len(items)), 3),
            "output_annotations_file": str(out_path),
        }

    def export_finetuning_dataset(
        self,
        items: List[DeeDatasetItem],
        output_file: str | Path,
        format_type: str = "chat_jsonl",
    ) -> int:
        """
        Exports labeled dataset items into standard Chat/Instruction JSONL format
        for fine-tuning Claude, OpenAI, or open-weight models.
        """
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for item in items:
                if not item.ground_truth:
                    continue

                # Run OCR to get document text prompt
                with open(item.file_path, "rb") as doc_f:
                    bytes_data = doc_f.read()

                ocr_res = self.ocr.process_document(bytes_data, mime_type=item.mime_type)
                ocr_text = ocr_res["text"]

                system_prompt, user_template = get_prompt_for_document_type(item.document_type)
                user_msg = user_template.replace("{{OCR_TEXT}}", ocr_text)
                assistant_msg = json.dumps(item.ground_truth.model_dump(mode="json"), ensure_ascii=False)

                if format_type == "chat_jsonl":
                    row = {
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": assistant_msg},
                        ],
                        "metadata": {
                            "item_id": item.item_id,
                            "document_type": item.document_type.value,
                            "language": item.language or ocr_res.get("detected_script") or "English",
                        }
                    }
                else:
                    row = {
                        "instruction": system_prompt,
                        "input": user_msg,
                        "output": assistant_msg,
                        "item_id": item.item_id,
                    }

                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1

        return count

    def export_few_shot_exemplars(
        self,
        items: List[DeeDatasetItem],
        output_file: str | Path,
        max_per_language: int = 2,
    ) -> Dict[str, Any]:
        """
        Builds a few-shot exemplar bank grouped by language and document type
        to inject into prompts for in-context learning.
        """
        bank: Dict[str, List[Dict[str, Any]]] = {}

        for item in items:
            if not item.ground_truth:
                continue

            lang = item.language or "English"
            bank.setdefault(lang, [])
            if len(bank[lang]) >= max_per_language:
                continue

            with open(item.file_path, "rb") as doc_f:
                bytes_data = doc_f.read()
            ocr_res = self.ocr.process_document(bytes_data, mime_type=item.mime_type)

            bank[lang].append({
                "item_id": item.item_id,
                "document_type": item.document_type.value,
                "ocr_snippet": ocr_res["text"][:1500],
                "ground_truth": item.ground_truth.model_dump(mode="json"),
            })

        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(bank, f, indent=2, ensure_ascii=False)

        return {"languages_covered": list(bank.keys()), "total_exemplars": sum(len(v) for v in bank.values())}


dee_dataset_manager = DeeDatasetManager()
