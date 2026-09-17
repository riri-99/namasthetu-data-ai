  The process begins with the user providing a folder of document images. These images undergo initial processing including OCR to recognize text and extract
  key information into a structured format. The system then scores the extraction results.

  Extraction results with high confidence are automatically approved, while those with lower confidence are sent for human review. Human corrections serve as ground truth. The system learns continuously from these corrections to improve its extraction accuracy through model retraining and fine-tuning.
  
  Here is how the training and learning pipeline works in simple terms, step-by-step:


  ## Step 1: Ingestion & Smart Reading

  1. What happens: You point the system to a folder of raw images or scanned PDFs.
  2. Under the hood:

      a. ocr.py automatically deskews, denoises, and enhances the contrast of faded stamp papers.

      b. It detects the regional script (e.g., Kannada, Marathi, Hindi, Telugu, Tamil, or English) and runs multilingual OCR.

      c. Sensitive PII (Aadhaar, PAN) is masked right away so personal data is never exposed.

  
  ## Step 2: First-Pass Extraction & Confidence Scoring

  1. What happens: The AI extracts structured fields (Vendor, Purchaser, Survey Number, Plot Area, SRO Registration, Encumbrances).
  2. Under the hood:

      a. prompts.py interprets regional legal terms (e.g., ಮಾರಾಟಗಾರ, विक्रेता, क्रेता) into universal English schema keys.

      b. pipeline.py calculates a Confidence Score (0.0 to 1.0) based on OCR readability and field certainty.

  
  ## Step 3: Traffic Cop (Routing High vs. Low Confidence)

  1. High Confidence (≥ 0.85):

      a. The extraction is marked as EXTRACTED and auto-approved.

  2. Low Confidence (< 0.85):

      a. The document is marked as REVIEWING and sent to the Ops triage queue.

      b. The pipeline attaches an actionable tip for the reviewer (e.g., "Survey number blurry on page 2, verify manually").

  
  ## Step 4: Creating Training Flashcards (Ground Truth)

  1. What happens: Whenever a human reviewer corrects a field or confirms an extraction:

      a. learning_loop.py captures the original raw document and the final corrected data.

      b. dataset_manager.py bundles them into clean JSONL training pairs (Prompt → Perfect JSON output).

  
  ## Step 5: Retraining & The Improvement Loop (Flywheel)

  1. What happens: Periodically (e.g., weekly or per batch of 500 documents), the newly exported training pairs are fed into fine-tuning.
  2. Result:

      a. The model learns difficult real-world quirks (smudged sub-registrar seals, regional legal phrasing, unconventional deed formats).

      b. On the next batch, fewer documents get sent to human review, and the auto-approval rate goes up.

  
