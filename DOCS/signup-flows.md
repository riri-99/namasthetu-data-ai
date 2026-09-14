# Sign-Up Flow Guide — 99acres, MagicBricks, NoBroker & Similar Property Portals

**Important note on sourcing:** This guide is compiled from each platform's own help/FAQ content, forum documentation, and publicly described UX patterns. It does **not** include literal screenshots of the live sign-up screens — I don't have a browser tool that can visit and capture these sites in real time, and several of them (99acres, NoBroker) actively block automated fetching. The images included in the accompanying PDF are **illustrative UI mockups**, not real captures of these specific websites. Screens, wording, and exact steps also change fairly often (A/B tests, redesigns), so treat step order as directionally correct rather than pixel-exact.

For each site, two personas are covered:
- **A. Casual/Normal visitor** — just browsing listings, saving searches, setting alerts.
- **B. Someone buying / renting / selling** — posting a property, contacting owners, using paid plans, etc. This path usually requires full registration and often extra fields (owner/dealer/builder type, RERA ID, etc.).

---

## 1. 99acres.com

### A. As a normal visitor
1. Land on **99acres.com** — you can browse listings, use filters (location, budget, BHK, property type) without logging in.
2. To view an owner's/agent's contact number, download a brochure, or save a search/alert, you're prompted to **Login/Register**.
3. Click **Menu (top-right) → Login/Register**.
4. A pop-up appears with two tabs: **Login** and **Register**.
5. On the Register tab, enter:
   - Name
   - Email address or mobile number
   - Password (if email route) or proceed via OTP (if mobile route)
6. Click **Register**. If mobile-based, an OTP is sent via SMS — enter it to verify.
7. If email-based, a verification link/email is sent — you may need to confirm it to fully activate the account.
8. Once verified, you're logged into **My99acres**, where you can save searches, get price/locality alerts, and shortlist properties.

### B. As someone looking to buy/rent/sell (posting a property)
1. Registration is **mandatory** to post a property — 99acres explicitly restricts one account per mobile number/email (no duplicate accounts).
2. From the homepage, click **"Post Property Free"** (or Menu → Post Property).
3. You're routed through the same **Login/Register** pop-up as above if not already signed in; this time you also choose your role: **Owner / Dealer (Agent) / Builder**.
4. After registering/logging in, you're taken to the **Property Posting Form**, completed in roughly 6 steps:
   1. Basic Details (I am a: Owner/Agent/Builder; property type — residential/commercial; sale or rent)
   2. Location Details (city, locality, project/society name, address)
   3. Property Profile (BHK, area, floor, age of property, furnishing, amenities)
   4. Photos/Video upload
   5. Pricing (expected price/rent, maintenance, price negotiable toggle)
   6. Review & Submit — listing then goes for a screening review (~24 hours) before going live.
5. If buying/renting rather than posting: once registered, clicking "Contact Owner/Agent" or "Get Phone Number" on a listing may prompt an additional mobile OTP verification even after login, as an anti-spam measure.
6. Account management (from My99acres dashboard, all needing login):
   - Change password: Settings → Change Password → enter new password → Save.
   - Edit email: Modify (under profile pic) → update Email ID tab.
   - Change mobile number: Modify → update Mobile Number tab (OTP re-verification required).
   - View/manage all listings: Manage Listings → All Listings.
   - Deactivate/delete account: not self-serve — requires contacting support (toll-free number or services@99acres.com).

---

## 2. MagicBricks.com

### A. As a normal visitor
1. Browse property listings, use search filters without an account.
2. To unlock an owner's contact number, save a property, or set an alert, click **Login** (top-right).
3. A modal offers: **Continue with Google**, **Continue with Facebook**, or **Mobile Number** login/registration.
4. If using mobile number: enter your 10-digit number → click **Get OTP** → enter the 6-digit OTP received via SMS → click **Verify/Continue**.
5. First-time users are typically asked to complete a short profile (name, email) right after OTP verification.
6. Once verified, you land on your MagicBricks dashboard where you can view saved properties, alerts, and shortlists.

### B. As someone looking to buy/rent/sell
1. Registration/login (same OTP-based flow as above) is required before posting a property or before revealing full owner contact details on many listings.
2. To **post a property**: click **"Post Property Free"** on the homepage.
3. After login/registration, choose your role: **Owner**, **Agent/Dealer**, or **Builder**.
4. Fill the posting form in stages:
   1. What do you want to do? (Sell / Rent / PG-Co-living)
   2. Property type & configuration (BHK, plot/flat/independent house, area)
   3. Locality & address (city, locality, landmark)
   4. Amenities & additional details (furnishing, parking, age, facing)
   5. Price expectations
   6. Photos upload (drives higher visibility/ranking)
   7. Review & Submit — goes through a verification/screening step before publishing.
5. To **contact an owner/agent**: click "View Number"/"Contact Owner" on a listing → if not logged in, triggers the same mobile-OTP login gate → number is revealed (sometimes with a masked/virtual number for privacy).
6. Paid options: MagicBricks offers premium listing/visibility packages (e.g., "Featured," "Premium") accessible from the seller dashboard once a property is posted — this is where payment details are collected, separate from the core sign-up.

---

## 3. NoBroker.com

NoBroker's core positioning is "zero brokerage," so sign-up is tightly coupled to whichever action you're taking (browse vs. post vs. buyer/rental-agreement services) — there isn't always a single generic "Sign Up" button; it often appears contextually.

### A. As a normal visitor
1. You can browse listings without an account.
2. Clicking on a listing to view more detail, or clicking **"Sign In/Sign Up"** (top-right on web; under "More" → scroll to bottom on the app) opens the auth flow.
3. Enter your **phone number** → click **Continue/Get OTP**.
4. Enter the OTP sent via SMS.
5. If you're a first-time user, you're then asked for **Name** and **Email ID**, then click **"Create Account."** Existing numbers skip straight to login after OTP.

### B. As someone looking to buy/rent/sell
**Selling/renting out a property:**
1. Visit NoBroker → click **"Post Your Free Ad"** on the homepage.
2. Enter location, then select **property type** and **ad type** (Sale/Rent/PG).
3. Sign up/login is triggered here if not already done (phone number + OTP + name/email, as above).
4. Fill in property details, locality details, rental/sale terms, and amenities.
5. Upload required photos and (in many flows) schedule an appointment for ad verification/approval before the ad goes live.
6. Optional: choose a **Seller Plan** (adds a relationship manager, professional photography, Facebook marketing, etc.) — this is presented after the free ad is posted.

**Buying a property:**
1. Visit NoBroker's buy section, browse properties.
2. Click **"Get Owner Details" / "Contact Builder"** on a listing.
3. Enter mobile number, name, and email → enter OTP sent to your phone.
4. Once verified, you can view the owner/builder's contact info and proceed with inquiries.
5. Optional: opt into a **Buyer Plan** (dedicated property expert + legal assistance) presented alongside search results.

**Rental agreement service (distinct sub-flow, still gated by the same phone-OTP account system):**
1. Go to the Rental Agreement service page → select a package → click **"Create Rental Agreement."**
2. Enter mobile number to view pricing (an additional ₹1,000 fee applies if you want personal assistance).
3. Choose your role: **"Continue as Tenant"** or **"Continue as Owner."**
4. Fill property & agreement details (date, rent, deposit; stamp duty is auto-calculated); optionally choose notarization.
5. Add both tenant and landlord details.
6. Optionally e-sign via **Aadhaar OTP** (both parties can digitally sign without meeting in person).

**Becoming a NoBroker agent/partner** (separate persona, worth noting since it surfaces in their forums):
- Contact NoBroker via their partner-enrollment channel or phone line, providing name, phone number, address, and a summary of experience — this is a manually reviewed application rather than a self-serve sign-up form.

---

## 4. Common Patterns Across These & Similar Sites (Housing.com, Square Yards, CommonFloor, etc.)

| Element | Typical Pattern |
|---|---|
| **Browsing** | No login required for basic search/browse |
| **Login gate triggers** | Viewing phone numbers, saving/shortlisting, posting a property, downloading brochures |
| **Primary identity** | Mobile number + OTP (dominant in India-focused portals) |
| **Secondary identity** | Email + password, or Google/Facebook social login |
| **Role selection** | Buyer/Tenant vs. Owner vs. Agent/Dealer vs. Builder — usually asked either at signup or at the start of the "Post Property" flow |
| **Anti-fraud/spam controls** | One account per mobile number (no duplicates), OTP re-verification even after login for sensitive actions (viewing contact info, changing number) |
| **Property posting steps** | Almost universally: Basic details → Location → Property profile/config → Photos → Pricing → Review/Submit → Screening/verification delay before going live |
| **Monetization touchpoint** | Comes *after* the free posting/browsing flow — premium visibility packages, relationship managers, legal/documentation services |

---

## 5. Practical Notes / Gaps

- **Flows change often:** These sites frequently run A/B tests on their auth modals (e.g., order of Google login vs. mobile OTP), so the *sequence* of buttons may shift even if the *data required* stays consistent.
- **Regional/app vs. web differences:** The mobile app flows (especially NoBroker's) sometimes differ slightly in menu placement from the desktop web flow, though the underlying OTP + role-selection logic is the same.