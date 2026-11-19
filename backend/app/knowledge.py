"""Curated knowledge documents, each tied to the official page it was taken from.

Only statements that appear on the platforms' own public pages are included. Anything
the assistant cannot ground in these documents or in the catalogue, it should say it
does not know and point to the official site.
"""
from __future__ import annotations

KNOWLEDGE: list[dict] = [
    {
        "id": "kb-darglobal-overview",
        "platform": "darglobal",
        "title": "About DarGlobal",
        "url": "https://darglobal.co.uk/",
        "text": (
            "DarGlobal is an international luxury real estate developer. Its project index lists developments in "
            "the United Arab Emirates (Dubai and Al Marjan Island, Ras Al Khaimah), Saudi Arabia (Riyadh and Jeddah), "
            "Oman (AIDA, Muscat), Qatar (Doha and Simaisma), Spain (Benahavís and Finca Cortesin on the Costa del Sol) "
            "and the United Kingdom (London). Project types are apartments, villas, hotel rooms and plots. "
            "DarGlobal's site also covers investor relations, press, hospitality, luxury golf communities, an "
            "exclusive membership programme, commercial projects, tokenization and a 'Premiere Edition' (1of1) "
            "collection of one-of-a-kind residences. Enquiries go through the 'Register your interest' form on each "
            "project page or the Get in touch page."
        ),
    },
    {
        "id": "kb-darglobal-partners",
        "platform": "darglobal",
        "title": "DarGlobal brand partners",
        "url": "https://darglobal.co.uk/partners/the-trump-organization",
        "text": (
            "DarGlobal's partner pages list these brand partners: Aston Martin (The Astera, Al Marjan Island), "
            "Elie Saab (Les Vagues, Doha), Fendi Casa (Azure Oceanfront Villas at AIDA and DarGlobal Mansions in "
            "Wadi Safar, Riyadh), Automobili Lamborghini (Tierra Viva and Painite Villas, Benahavís), Marriott "
            "(Marriott Residences, AIDA), Missoni (Urban Oasis, Dubai and Marea, Finca Cortesin), Mouawad (Neptune "
            "villas, Riyadh), Pagani (Da Vinci Tower and the Pagani Penthouse, Dubai), The Trump Organization "
            "(Trump International Hotel & Tower Dubai, Trump Tower Jeddah, Trump Plaza Jeddah residences, Trump "
            "Mansions in Wadi Safar, Trump International Simaisma and the Trump hotel, Cliff Villas and Golf Villas "
            "at AIDA), W Hotels (W Residences, Downtown Dubai) and Paramount (Nickelodeon Hotels & Resorts at AIDA)."
        ),
    },
    {
        "id": "kb-darglobal-pricing",
        "platform": "darglobal",
        "title": "DarGlobal prices and availability",
        "url": "https://darglobal.co.uk/projects",
        "text": (
            "DarGlobal's project pages do not publish prices or payment plans. Prices, unit availability and payment "
            "plans are shared by DarGlobal's sales team after you register interest on the project page. Two Dubai "
            "projects, Urban Oasis by Missoni and W Residences, are listed as completed and sold out; buyers can ask "
            "DarGlobal about the secondary market."
        ),
    },
    {
        "id": "kb-aida",
        "platform": "darglobal",
        "title": "AIDA, Muscat (Oman)",
        "url": "https://darglobal.co.uk/landing-page/aida",
        "text": (
            "AIDA is a gated hilltop community and golfing destination in Muscat, 130 metres above sea level and "
            "about 25 minutes from Muscat International Airport. DarGlobal's AIDA collections include the Trump "
            "International Hotel (rooms and suites with professional management and two weeks of personal use a "
            "year), Trump Cliff Villas, Trump Golf Villas, Fairway Villas, Azure Oceanfront Villas by Fendi Casa, "
            "Marriott Residences, The Great Escape 1 and 2, Coastal Investment Villas, Sunrise Haven, Amour Sans "
            "Détour 1 and 2, and Nickelodeon Hotels & Resorts. DarGlobal's Oman pages state 100% foreign ownership "
            "in special economic and free zones and that Oman applies the inheritance laws of the investor's "
            "country of origin."
        ),
    },
    {
        "id": "kb-wasalt-overview",
        "platform": "wasalt",
        "title": "About Wasalt",
        "url": "https://wasalt.sa/en",
        "text": (
            "Wasalt is a Saudi real estate platform licensed by the Real Estate General Authority (REGA licence "
            "1200016591) and the Ministry of Tourism (licence 73106008, accommodation and unit reservation). It "
            "lists residential and commercial properties for sale and rent across Saudi Arabia, including Riyadh, "
            "Jeddah, Makkah, Madinah, Dammam and Al Khobar, in Arabic and English, without requiring login to "
            "browse. Services include property search, projects and masterplans, online auctions, daily rentals, "
            "barter listings, Matchmaker and the Wasalt Business app for brokers. Owners can list a property via the "
            "website ('Post Property'), the Wasalt app or the Wasalt Business app. Customer care number: 8001233227."
        ),
    },
    {
        "id": "kb-wasalt-auctions",
        "platform": "wasalt",
        "title": "Wasalt Auctions",
        "url": "https://auction.wasalt.sa/en",
        "text": (
            "Wasalt Auctions is a feature where real estate assets are sold through timed auctions; bidders compete "
            "to determine the final sale price. Auctions include assets from private sellers and assets offered in "
            "collaboration with Infath (the Entrustment and Liquidation Center), spanning real estate, vehicles and "
            "movable assets across Saudi Arabia."
        ),
    },
    {
        "id": "kb-wasalt-matchmaker",
        "platform": "wasalt",
        "title": "Wasalt Matchmaker",
        "url": "https://business.wasalt.sa/en",
        "text": (
            "Matchmaker helps property owners and brokers find potential leads based on their live listings. It "
            "matches leads by property type, purpose, district and category of the live property, and is set up in "
            "the Wasalt Business app. Buyers and tenants can use 'Get Matched' on Wasalt to share their requirements "
            "and be connected with relevant property experts."
        ),
    },
    {
        "id": "kb-wasalt-daily",
        "platform": "wasalt",
        "title": "Wasalt Daily Rentals",
        "url": "https://wasalt.sa/en/wb-daily-rentals",
        "text": (
            "Wasalt offers daily rentals (short stays) alongside long-term rentals. Property owners can list daily "
            "rentals with Wasalt; the homepage highlights weekly earnings, free coverage and competitive commission "
            "rates for hosts."
        ),
    },
    {
        "id": "kb-wasalt-data-note",
        "platform": "wasalt",
        "title": "How this assistant uses Wasalt data",
        "url": "https://wasalt.sa/llms.txt",
        "text": (
            "The Wasalt listings in this assistant are a dated snapshot of Wasalt's public category pages, used to "
            "recommend and summarise listings with attribution ('Source: Wasalt.sa'). Prices, availability and "
            "listing status change often, so every result links to the live Wasalt listing or search page for "
            "current details."
        ),
    },
]
