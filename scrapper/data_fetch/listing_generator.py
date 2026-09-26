"""
Corridor Real Estate Listing Generator
Converts extracted society records into full PropertyListing TypeScript and SQL seed files
matching DOCS/mockProperties.ts data shape.
"""

import os
import sys
import re
import json
import random
import hashlib
import pandas as pd
from typing import Dict, Any, List

# Ensure utf-8 stdout
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Curated high-resolution Unsplash luxury property images
CURATED_IMAGES = {
    "exterior": [
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=1200&q=80",
    ],
    "living": [
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600566752355-35792bedcfea?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600573472591-ee6b68d14c68?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&q=80",
    ],
    "bedroom": [
        "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1617325247661-675ab4b64ae2?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1598928506311-c55ded91a20c?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&q=80",
    ],
    "kitchen": [
        "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1556912173-3bb406ef7e77?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1507089947368-19c1da9775ae?auto=format&fit=crop&w=1200&q=80",
    ],
    "balcony_view": [
        "https://images.unsplash.com/photo-1600573472550-8090b5e0745e?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1571888164858-a8bf388ea8c9?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?auto=format&fit=crop&w=1200&q=80",
    ],
}

OWNER_AVATARS = [
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80",
    "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=200&q=80",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80",
    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=200&q=80",
    "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=200&q=80",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=200&q=80",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=200&q=80",
]

# Corridor-specific config
CITY_CONFIG = {
    "Pune": {
        "state": "Maharashtra",
        "currency": "INR",
        "price_per_sqft_range": (9500, 23500),
        "maintenance_per_sqft": (3.5, 6.0),
        "stamp_rate": "6%",
        "reg_fee": "₹30,000",
        "water_options": [
            "PMC Direct + 24/7 Society Borewell",
            "PMC High-Pressure Direct + Water Softening Plant",
            "Dual PMC Potable + Automated Rainwater Harvesting",
        ],
        "inspectors": [
            "Er. Ramesh S. Rao, M.Tech Civil (NICMAR)",
            "Er. Arvind Hegde, B.E Civil, Structural Specialist",
            "Er. Priya Deshmukh, Chartered Assessor (Pune)",
            "Er. Makarand Chitale, PE Structural (COEP)",
        ],
        "owner_names": [
            "S. Venkatraman", "Rohit Kulkarni", "Dr. Arvind Joshi", "Sunita Deshmukh",
            "Anand Patwardhan", "Rohan Shinde", "Deepak Kirloskar", "Neha Bhave",
            "Aditya Ranade", "Tanvi Godbole", "Sachin Tendulkar", "Pooja Chordia"
        ],
        "phone_prefix": "+91 98",
        "schools": [
            "The Bishop's School (1.8 km)", "Symbiosis International (2.4 km)",
            "Vibgyor High Balewadi (1.5 km)", "St. Mary's School (3.2 km)",
            "Delhi Public School Pune (2.1 km)", "Loyola High School (2.8 km)"
        ],
        "hospitals": [
            "Ruby Hall Clinic (2.2 km)", "Jehangir Hospital (3.1 km)",
            "Manipal Hospital Kharadi (1.6 km)", "Jupiter Hospital Baner (1.2 km)",
            "Sahyadri Hospital (2.5 km)"
        ],
        "metro_prefix": "Pune Metro Line 3 / Line 1",
        "metro_dist_range": (350, 2400),
        "appreciation_tag": "+38% (Pune Metro Line 3 & Ring Road Expansion)",
        "kyc": "DIGILOCKER_VERIFIED",
        "title_descriptors": [
            "with Panoramic Sahyadri Hills Vista & Deck",
            "Luxury High-Rise with Expansive Balcony",
            "Ultra-Luxury Residence with Private Foyer",
            "with Sunrise Facing Balcony & 3D Twin",
            "Premium Corner Suite with Italian Marble",
        ]
    },
    "Dubai": {
        "state": "Dubai Emirate",
        "currency": "AED",
        "price_per_sqft_range": (1850, 4200),
        "maintenance_per_sqft": (14.0, 26.0),
        "stamp_rate": "4% DLD",
        "reg_fee": "AED 4,000",
        "water_options": [
            "DEWA Potable Grid + Dual Chiller Loop",
            "DEWA District Cooling + Automated Desalination Filtration",
            "Direct DEWA Potable + Centralized RO Purification",
        ],
        "inspectors": [
            "Eng. Tariq Al-Mansoor, Chartered Civil Engineer (Dubai Municipality)",
            "Er. David Sterling, CEng MICE (RICS Chartered)",
            "Eng. Fatima Al-Zahra, Structural Assessor (DM Reg #8842)",
            "Eng. Zayd Al-Hashemi, Senior Quality Auditor (Trakhees)",
        ],
        "owner_names": [
            "Sheikh Hamdan Al-Falasi", "Omar Al-Hashimi", "David Sterling",
            "Sanjay Khubchandani", "Elena Rostova", "Marcus Vance",
            "Khalid Bin Rashid", "Farah Mansour", "Alexander Wright",
            "Nour Al-Sabah", "Vikramaditya Oberoi", "Sophia Chen"
        ],
        "phone_prefix": "+971 50 ",
        "schools": [
            "Dubai College (3.1 km)", "Kings' School Dubai (2.4 km)",
            "American School of Dubai (3.5 km)", "GEMS Wellington International (2.8 km)",
            "Jumeirah English Speaking School (4.0 km)"
        ],
        "hospitals": [
            "Mediclinic City Hospital (2.1 km)", "American Hospital Dubai (3.0 km)",
            "King's College Hospital Dubai Hills (2.5 km)", "Aster Hospital Mankhool (3.2 km)"
        ],
        "metro_prefix": "Dubai Metro Red / Green Line",
        "metro_dist_range": (200, 1800),
        "appreciation_tag": "+44% (Al Maktoum Airport & Blue Line Metro Synergy)",
        "kyc": "UAE_PASS_VERIFIED",
        "title_descriptors": [
            "with Palm Jumeirah & Marina Skyline View",
            "Waterfront Luxury Suite with Floor-to-Ceiling Glazing",
            "Ultra-Prime High-Rise with Burj Khalifa Vista",
            "with Expansive Sea Deck & Italian Kitchen",
            "Trophy Residence with Dedicated Valet & Concierge",
        ]
    },
    "Mumbai": {
        "state": "Maharashtra",
        "currency": "INR",
        "price_per_sqft_range": (29000, 76000),
        "maintenance_per_sqft": (8.0, 18.0),
        "stamp_rate": "6%",
        "reg_fee": "₹30,000",
        "water_options": [
            "BMC Direct High-Pressure + 24/7 RO",
            "BMC 24/7 Continuous Municipal Connection + Dual Sump",
            "Direct BMC High-Capacity Reservoirs + UV Disinfection",
        ],
        "inspectors": [
            "Er. Vikram Kulkarni, PE Structural (Mumbai)",
            "Er. Aniruddha Mehta, Chartered Civil Assessor",
            "Er. Neha Parekh, Structural Auditor (MCGM Empanelled)",
            "Er. Cyrus Contractor, M.Tech Civil (IIT Bombay)",
        ],
        "owner_names": [
            "Cyrus M. Mehta", "Harshvardhan Singhania", "Gautam Piramal",
            "Ananya Sen", "Dr. Rajiv Godrej", "Meera Merchant",
            "Kavita Jhunjhunwala", "Aditya Birla Trust", "Pravin Shah",
            "Rohan Vora", "Farida Batliwala", "Siddharth Wadia"
        ],
        "phone_prefix": "+91 98",
        "schools": [
            "The Cathedral & John Connon (3.5 km)", "Bombay Scottish School (2.2 km)",
            "Dhirubhai Ambani International School (4.1 km)", "American School of Bombay (3.8 km)",
            "St. Xavier's High School (2.9 km)"
        ],
        "hospitals": [
            "Breach Candy Hospital (2.0 km)", "Jaslok Hospital (2.5 km)",
            "Lilavati Hospital Bandra (1.8 km)", "Kokilaben Dhirubhai Ambani Hospital (3.4 km)",
            "Hinduja Hospital Mahim (2.1 km)"
        ],
        "metro_prefix": "Mumbai Metro Line 3 (Aqua Line) / Western Line",
        "metro_dist_range": (250, 1600),
        "appreciation_tag": "+35% (Coastal Road & Worli-Sewri Connector Synergy)",
        "kyc": "DIGILOCKER_VERIFIED",
        "title_descriptors": [
            "with Arabian Sea View & High-Rise Sun Deck",
            "Trophy Tower Residence with Armani / Casa Finishes",
            "Ultra-Prime Sea-Facing Suite with Private Foyer",
            "with Unobstructed Coastline Vista & Digital Twin",
            "Signature Penthouse Floor with 11ft Ceilings",
        ]
    },
    "Indore": {
        "state": "Madhya Pradesh",
        "currency": "INR",
        "price_per_sqft_range": (6200, 13800),
        "maintenance_per_sqft": (2.2, 4.2),
        "stamp_rate": "7.5%",
        "reg_fee": "₹35,000",
        "water_options": [
            "IMC Narmada Water Supply Phase-III + Deep Borewell",
            "IMC Direct Potable Line + Society Water Softening Plant",
            "Dual Narmada Continuous Supply + Rainwater Harvesting",
        ],
        "inspectors": [
            "Er. Amit Chhabra, Chartered Civil Assessor (MP)",
            "Er. Rajesh Singhal, M.Tech Civil (SGSITS Indore)",
            "Er. Kavita Verma, Structural Auditor (IMC Empanelled)",
            "Er. Sunil Patidar, PE Structural (Indore)",
        ],
        "owner_names": [
            "Rajesh Singhal", "Ankit Agrawal", "Priya Sharma",
            "Dr. Sunil Chhajed", "Vikramaditya Mittal", "Vandana Patidar",
            "Deepak Porwal", "Shalini Mahajan", "Rameshwar Neema",
            "Alok Jhavar", "Sudhir Garg", "Nidhi Khandelwal"
        ],
        "phone_prefix": "+91 94",
        "schools": [
            "The Daly College (2.8 km)", "Delhi Public School Indore (3.2 km)",
            "Choithram International (2.1 km)", "Emerald Heights International School (4.5 km)",
            "Shishukunj International School (3.8 km)"
        ],
        "hospitals": [
            "Medanta Super Specialty Hospital (2.0 km)", "Bombay Hospital Indore (1.5 km)",
            "CHL Hospital (2.8 km)", "Apollo Hospitals Vijay Nagar (1.8 km)"
        ],
        "metro_prefix": "Indore Metro Yellow Line",
        "metro_dist_range": (400, 2600),
        "appreciation_tag": "+45% (Indore Metro Priority Ring & Super Corridor Hub)",
        "kyc": "DIGILOCKER_VERIFIED",
        "title_descriptors": [
            "with Private Terrace Garden & Green Vista",
            "Luxury Independent Floor with Italian Flooring",
            "Super Corridor Facing Residence with Clubhouse Access",
            "with Modern Modular Kitchen & 3D Spatial Twin",
            "Exclusive Corner Villa Suite with Private Lawn",
        ]
    }
}

AMENITIES_POOL = {
    "standard": [
        "Clubhouse & 25m Heated Lap Pool",
        "24/7 Power Backup (100% DG)",
        "Dedicated EV 7.4kW Fast Charger",
        "State-of-the-art Gymnasium & Yoga Studio",
        "Biometric Access Lobby & 3-Tier Security",
        "Children's Play Area & Landscaped Garden",
        "Rainwater Harvesting & Solar Water Heating",
    ],
    "ultra": [
        "Private Screening Cinema (20-30 Seats)",
        "Rooftop Infinity Pool & Sky Deck",
        "Concierge Service & Valet Parking",
        "Squash & Badminton International Courts",
        "Private Plunge Pool & Sun Deck",
        "Smart Home Automation by Control4 / Lutron",
        "Helipad Access on Society Tower",
    ],
    "dubai": [
        "Private Beach Access & Yacht Marina Berth",
        "Burj Khalifa & Palm Panoramic Sky Lounge",
        "24/7 Quintessentially Luxury Concierge",
        "Temperature-Controlled Infinity Horizon Pool",
        "Chauffeur & Valet Basement Parking",
        "Hydrotherapy Spa & Turkish Hammam",
        "Direct Skybridge Access to Retail Galleria",
    ]
}

def clean_slug(text: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower()).strip('-')
    return s[:60]

def format_inr(paise: int) -> str:
    rupees = paise // 100
    if rupees >= 10000000:
        cr = rupees / 10000000
        return f"₹{cr:.2f} Cr"
    elif rupees >= 100000:
        lakh = rupees / 100000
        return f"₹{lakh:.2f} L"
    else:
        return f"₹{rupees:,}"

def get_ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def generate_property_from_row(row: pd.Series, global_idx: int) -> Dict[str, Any]:
    city = row['city']
    cfg = CITY_CONFIG.get(city, CITY_CONFIG["Pune"])
    
    # Deterministic seed based on row id
    row_id_str = str(row['id'])
    seed_val = int(hashlib.md5(row_id_str.encode('utf-8')).hexdigest()[:8], 16)
    rng = random.Random(seed_val)
    
    # Configuration and Property Type
    raw_pt = str(row.get('property_type', ''))
    if 'Villa' in raw_pt:
        prop_type = "Villa"
        configs = ["4 BHK", "5 BHK"]
        cfg_choice = rng.choice(configs)
        bathrooms = 5 if cfg_choice == "5 BHK" else 4
        carpet = rng.randint(3200, 5200)
    elif 'Township' in raw_pt:
        prop_type = "Apartment"
        configs = ["3 BHK", "4 BHK"]
        cfg_choice = rng.choice(configs)
        bathrooms = 4 if cfg_choice == "4 BHK" else 3
        carpet = rng.randint(1800, 2900)
    elif 'Ultra-Luxury' in raw_pt:
        prop_type = rng.choice(["Apartment", "Penthouse"])
        configs = ["3 BHK", "4 BHK", "5 BHK"]
        cfg_choice = rng.choice(configs)
        bathrooms = 4 if cfg_choice in ["4 BHK", "5 BHK"] else 3
        carpet = rng.randint(2200, 4200)
    else:
        prop_type = "Apartment"
        configs = ["2 BHK", "3 BHK", "4 BHK"]
        weights = [0.25, 0.55, 0.20]
        cfg_choice = rng.choices(configs, weights=weights)[0]
        bathrooms = 2 if cfg_choice == "2 BHK" else (3 if cfg_choice == "3 BHK" else 4)
        carpet = rng.randint(950, 1300) if cfg_choice == "2 BHK" else (rng.randint(1450, 2100) if cfg_choice == "3 BHK" else rng.randint(2300, 3100))
    
    super_built = int(carpet * rng.uniform(1.24, 1.32))
    
    # Listing Mode (85% Buy, 15% Rent)
    listing_mode = "RENT" if rng.random() < 0.15 else "BUY"
    
    # Price Calculation
    sqft_rate = rng.randint(cfg["price_per_sqft_range"][0], cfg["price_per_sqft_range"][1])
    
    if city == "Dubai":
        # Dubai in AED
        total_aed = carpet * sqft_rate
        if listing_mode == "BUY":
            formatted_price = f"AED {total_aed:,.0f}"
            price_per_sqft = f"AED {sqft_rate:,} / sq.ft"
            price_paise = str(total_aed * 100) # stored in fils/cents
            maint_monthly = int((super_built * rng.uniform(cfg["maintenance_per_sqft"][0], cfg["maintenance_per_sqft"][1])) / 12)
            maintenance_paise = str(maint_monthly * 100)
            stamp_est = f"AED {int(total_aed * 0.04):,} (4% DLD Transfer Fee)"
            reg_est = "AED 4,000 (DLD Trustee Fee)"
        else:
            annual_rent_aed = int(total_aed * rng.uniform(0.065, 0.085))
            monthly_rent_aed = annual_rent_aed // 12
            formatted_price = f"AED {monthly_rent_aed:,} / mo"
            price_per_sqft = f"AED {round(monthly_rent_aed / carpet, 1)} / sq.ft / mo"
            price_paise = str(monthly_rent_aed * 100)
            maintenance_paise = "0"
            stamp_est = "AED 1,050 (Ejari Registration)"
            reg_est = "AED 2,000 (Refundable Deposit)"
    else:
        # India in INR
        total_inr = carpet * sqft_rate
        if listing_mode == "BUY":
            total_paise = total_inr * 100
            price_paise = str(total_paise)
            formatted_price = format_inr(total_paise)
            price_per_sqft = f"₹{sqft_rate:,} / sq.ft"
            maint_monthly_inr = int(super_built * rng.uniform(cfg["maintenance_per_sqft"][0], cfg["maintenance_per_sqft"][1]))
            maintenance_paise = str(maint_monthly_inr * 100)
            stamp_val = int(total_inr * (0.06 if "Maharashtra" in cfg["state"] else 0.075))
            stamp_est = f"{format_inr(stamp_val * 100)} ({cfg['stamp_rate']})"
            reg_est = cfg["reg_fee"]
        else:
            annual_rent_inr = int(total_inr * rng.uniform(0.032, 0.045))
            monthly_rent_inr = annual_rent_inr // 12
            monthly_paise = monthly_rent_inr * 100
            price_paise = str(monthly_paise)
            formatted_price = f"₹{monthly_rent_inr:,} / mo"
            price_per_sqft = f"₹{round(monthly_rent_inr / carpet, 1)} / sq.ft / mo"
            maint_monthly_inr = int(super_built * 3.5)
            maintenance_paise = str(maint_monthly_inr * 100)
            stamp_est = "₹1,500 (E-Registration)"
            reg_est = f"₹{monthly_rent_inr * 2:,} (Security Deposit)"
    
    # Title & Slug
    soc_name = str(row['name'])
    desc = rng.choice(cfg["title_descriptors"])
    title = f"{soc_name} {cfg_choice} {desc}"
    slug = f"{clean_slug(soc_name)}-{cfg_choice.lower().replace(' ', '')}-{global_idx+1}"
    
    # Floor
    levels = int(row.get('levels', 0)) if pd.notnull(row.get('levels')) else 0
    if prop_type == "Villa":
        floor_str = rng.choice(["G + 2 Independent Villa", "G + 1 Luxury Villa", "G + 2 Private Duplex Villa"])
    elif levels > 2:
        unit_floor = rng.randint(2, max(2, levels - 1))
        floor_str = f"{get_ordinal(unit_floor)} of {levels} Floors"
    else:
        tot_floors = rng.randint(12, 36)
        unit_floor = rng.randint(3, tot_floors - 2)
        floor_str = f"{get_ordinal(unit_floor)} of {tot_floors} Floors"
    
    # Coordinates
    lat = round(float(row['latitude']), 6)
    lng = round(float(row['longitude']), 6)
    
    # Images (deterministic selection)
    ext_img = rng.choice(CURATED_IMAGES["exterior"])
    liv_img = rng.choice(CURATED_IMAGES["living"])
    bed_img = rng.choice(CURATED_IMAGES["bedroom"])
    kit_img = rng.choice(CURATED_IMAGES["kitchen"])
    bal_img = rng.choice(CURATED_IMAGES["balcony_view"])
    images = [ext_img, liv_img, bed_img, kit_img, bal_img]
    
    # ULPIN / Cadastral
    if city == "Dubai":
        makani = str(row.get('makani_number', ''))
        ulpin = makani if makani and makani != 'nan' else f"{rng.randint(10000, 99999)} {rng.randint(10000, 99999)}"
        rera_num = str(row.get('dld_project_id', f"DLD-PRJ-{rng.randint(70000, 99999)}"))
    else:
        st_code = "27" if city in ["Pune", "Mumbai"] else "23"
        dist_code = "25" if city == "Pune" else ("01" if city == "Mumbai" else "12")
        ulpin = f"{st_code}{dist_code}-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}-{rng.randint(10, 99)}"
        raw_rera = str(row.get('maharera_reg_no', ''))
        rera_num = raw_rera if raw_rera and raw_rera != 'nan' else f"P{st_code}{rng.randint(10000000, 99999999)}"
    
    # Categories
    cats = ["DIRECT_OWNER", "DIGITAL_TWIN", "TRUST_PASS_ELITE", "GATED_COMMUNITIES"]
    if listing_mode == "BUY":
        cats.append("TOP_AVM_DEALS")
    if prop_type == "Villa":
        cats.append("VILLAS_PLOTS")
    if "Sea" in title or "Palm" in title or "Marina" in title or "Coastline" in title:
        cats.append("WATERFRONT")
    if listing_mode == "RENT":
        cats.append("HIGH_RENTAL_YIELD")
    
    # Spatial Rooms
    spatial_rooms = [
        {
            "id": "living",
            "name": "Grand Living & Dining Pavilion",
            "dimensions": f"{rng.randint(22, 28)}' x {rng.randint(15, 18)}'",
            "carpetSqft": int(carpet * 0.30),
            "highlight": "Imported Italian marble flooring with floor-to-ceiling panoramic glass facade",
            "wallColor": rng.choice(["#FAF8F5", "#F4F1EA", "#F7F5F0"]),
            "floorType": "Imported Italian Marble"
        },
        {
            "id": "master",
            "name": "Master Suite with Walk-In Wardrobe",
            "dimensions": f"{rng.randint(18, 22)}' x {rng.randint(14, 16)}'",
            "carpetSqft": int(carpet * 0.24),
            "highlight": "Acoustic German double-glazed windows and engineered oak wood finish",
            "wallColor": rng.choice(["#ECEAE4", "#EDE7DC", "#F0EDE8"]),
            "floorType": "Engineered Oak Hardwood"
        },
        {
            "id": "kitchen",
            "name": "Modular Island Gourmet Kitchen",
            "dimensions": f"{rng.randint(14, 16)}' x {rng.randint(11, 13)}'",
            "carpetSqft": int(carpet * 0.14),
            "highlight": "Quartz stone countertop, built-in Bosch/Miele induction hob and chimney",
            "wallColor": "#FFFFFF",
            "floorType": "Anti-Skid Honed Quartzite"
        },
        {
            "id": "terrace",
            "name": "Sky Balcony & Sun Deck",
            "dimensions": f"{rng.randint(14, 18)}' x {rng.randint(6, 9)}'",
            "carpetSqft": int(carpet * 0.10),
            "highlight": "Open panoramic skyline vistas with tempered safety glass balustrade",
            "wallColor": "#E8ECE9",
            "floorType": "Rustic Weatherproof Decking"
        }
    ]
    
    # Inspection 80-pt audit
    inspector = rng.choice(cfg["inspectors"])
    scores = {
        "composite": rng.randint(94, 99),
        "structural": rng.randint(96, 100),
        "plumbing": rng.randint(93, 98),
        "electrical": rng.randint(93, 99),
        "finishes": rng.randint(95, 99),
        "cadastral": rng.randint(97, 100),
    }
    inspection = {
        "id": f"insp-{8000 + global_idx}",
        "inspectorName": inspector,
        "inspectionDate": f"{rng.randint(10, 28)} {rng.choice(['Jan', 'Feb', 'Mar'])} 2026",
        "scores": scores,
        "verifiedPointsCount": 80,
        "seepageDetected": False,
        "activeLiens": False,
        "ulpin": ulpin,
        "summary": f"Grade A structural resilience certified. Complete 80-point civil inspection verified with 0% moisture seepage and optimal electrical grounding. Cadastral boundary verified with DGPS precision.",
        "keyFindings": [
            {"category": "Structural & RCC", "status": "PASS", "detail": f"Rebound hammer test showed {round(rng.uniform(36.5, 42.0), 1)} N/mm² compressive strength (M35 benchmark). No deflection."},
            {"category": "Plumbing & Moisture", "status": "PASS", "detail": f"FLIR thermal imaging recorded {round(rng.uniform(7.5, 10.5), 1)}% relative dampness (Well below 15% threshold)."},
            {"category": "Electrical Safety", "status": "PASS", "detail": "Dual RCCB trip latency clocked at 21ms. Society earth pit resistance 1.2 Ohms."},
            {"category": "Cadastral / Legal", "status": "OPTIMAL", "detail": f"ULPIN {ulpin} cross-verified with official registry survey boundary without encumbrances."}
        ],
        "pdfUrl": f"/reports/{slug}-audit.pdf"
    }
    
    # Valuation AVM
    discount_pct = round(rng.uniform(2.5, 5.8), 1)
    if city == "Dubai":
        fair_market_paise = str(int(int(price_paise) * (1 + discount_pct / 100)))
        monthly_rent_val = str(int(int(price_paise) * 0.0062))
    else:
        fair_market_paise = str(int(int(price_paise) * (1 + discount_pct / 100)))
        monthly_rent_val = str(int(int(price_paise) * 0.0035))
        
    valuation = {
        "fairMarketPricePaise": fair_market_paise,
        "listedPricePaise": price_paise,
        "differencePercentage": -discount_pct,
        "marketPosition": "BELOW_AVM",
        "grossYieldPercentage": round(rng.uniform(4.2, 5.8), 1) if city == "Dubai" else round(rng.uniform(3.4, 4.8), 1),
        "monthlyRentalEstimatePaise": monthly_rent_val,
        "projected5YrAppreciation": cfg["appreciation_tag"],
        "historicalTransactionsCount": rng.randint(8, 28)
    }
    
    # Deed History
    deed_history = [
        {"year": "2026", "eventType": "INSPECTION_AUDIT", "title": "80-Point Physical Civil & Spatial Twin Audit", "parties": "Amberstone Engineering Bureau", "status": "VERIFIED"},
        {"year": "2024", "eventType": "ULPIN_SEEDED", "title": f"Digitized Cadastral Seeding (ULPIN {ulpin})", "parties": f"{cfg['state']} Revenue & Land Dept", "status": "VERIFIED"},
        {"year": "2021", "eventType": "SALE_DEED", "title": "Registered Absolute Conveyance Deed", "parties": f"{row['developer_name']} → Owner", "status": "VERIFIED"}
    ]
    
    # Owner KYC
    owner_name = rng.choice(cfg["owner_names"])
    phone_sub = f"{rng.randint(10000, 99999)}"
    owner = {
        "id": f"own-{100 + (global_idx % 400)}",
        "fullName": owner_name,
        "avatarUrl": rng.choice(OWNER_AVATARS),
        "kycStatus": cfg["kyc"],
        "joinedDate": f"{rng.choice(['January', 'March', 'June', 'October', 'November'])} 2024",
        "responseTime": "< 30 minutes" if rng.random() > 0.5 else "< 45 minutes",
        "phoneMasked": f"{cfg['phone_prefix']} •••••",
        "unredactedPhone": f"{cfg['phone_prefix']}{phone_sub}",
        "unredactedWhatsApp": f"{cfg['phone_prefix']}{phone_sub}"
    }
    
    # Amenities
    amenities = AMENITIES_POOL["dubai"] if city == "Dubai" else (AMENITIES_POOL["ultra"] if prop_type == "Villa" or "Ultra" in raw_pt else AMENITIES_POOL["standard"])
    
    # Neighbourhood
    metro_dist = rng.randint(cfg["metro_dist_range"][0], cfg["metro_dist_range"][1])
    neighbourhood = {
        "metroDistanceMeters": metro_dist,
        "schoolsNearby": rng.sample(cfg["schools"], 2),
        "hospitalNearby": rng.choice(cfg["hospitals"]),
        "waterSecurityIndex": f"High ({rng.randint(93, 99)}/100) — Direct continuous municipal feed"
    }
    
    return {
        "id": f"prop-{global_idx + 1}",
        "slug": slug,
        "societyId": row_id_str,
        "title": title,
        "locality": str(row['micro_market']),
        "city": city,
        "state": cfg["state"],
        "coordinates": {"lat": lat, "lng": lng},
        "listingMode": listing_mode,
        "category": cats,
        "propertyType": prop_type,
        "configuration": cfg_choice,
        "bathrooms": bathrooms,
        "carpetAreaSqft": carpet,
        "superBuiltUpAreaSqft": super_built,
        "floor": floor_str,
        "facing": rng.choice(["East", "West", "North-East", "North", "South-East"]),
        "waterSupply": rng.choice(cfg["water_options"]),
        "pricePaise": price_paise,
        "formattedPrice": formatted_price,
        "pricePerSqft": price_per_sqft,
        "maintenanceMonthlyPaise": maintenance_paise,
        "stampDutyEstimate": stamp_est,
        "registrationEstimate": reg_est,
        "images": images,
        "has3dTour": True,
        "spatialRooms": spatial_rooms,
        "trustScore": scores["composite"],
        "verifiedOwnerBadge": True,
        "topBadge": f"Owner Direct · {soc_name[:20]}" if len(soc_name) > 20 else f"Owner Direct · {soc_name}",
        "ulpin": ulpin,
        "reraNumber": rera_num,
        "availableFrom": rng.choice(["Immediate / Ready to Move", "Immediate", "Within 15 Days", "Within 30 Days"]),
        "inspection": inspection,
        "valuation": valuation,
        "deedHistory": deed_history,
        "owner": owner,
        "amenities": amenities,
        "neighbourhood": neighbourhood,
    }
