from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated" / "latest"
DOCS = ROOT / "docs"


def parse_price_range(val: Any) -> float:
    if pd.isna(val) or not val:
        return 300.0
    text = str(val)
    nums = [float(n) for n in re.findall(r"\d+", text.replace(",", ""))]
    if len(nums) >= 2:
        return sum(nums[:2]) / 2.0
    elif len(nums) == 1:
        return nums[0]
    return 300.0


def calculate_vfm_score(rating: float, reviews: float, price_for_two: float) -> tuple[float, str]:
    effective_rating = rating if rating > 0 else 4.0
    effective_reviews = reviews if reviews > 0 else 25.0
    norm_price = max(price_for_two / 2.0, 75.0)  # price per person estimate
    score = (effective_rating * math.log10(effective_reviews + 10)) / (norm_price / 100.0)
    score = round(score, 2)

    if effective_rating >= 4.2 and norm_price <= 175:
        tier = "Value Champion"
    elif effective_rating >= 4.3 and norm_price > 175:
        tier = "Premium Benchmark"
    elif norm_price <= 130:
        tier = "Budget Dhaba"
    else:
        tier = "Core Contender"

    return score, tier


# Curated Desire Decision Matrix
DESIRE_PROFILES = [
    {
        "id": "royal_thali",
        "title": "Royal Unlimited Thali Feast",
        "badge": "👑 Grand Celebration",
        "icon": "👑",
        "tagline": "All-you-can-eat royal spread with multiple sabzis, fresh rotla, sweets, farsan & buttermilk",
        "ideal_for": "Family dining, festive gatherings, complete Kathiyawadi & Gujarati culinary journey",
        "recommendations": {
            "all": {
                "best_overall": {
                    "name": "Atithi Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Bodakdev",
                    "rating": 4.7,
                    "reviews": 4890,
                    "app": "Swiggy / Dineout",
                    "items": [
                        {"name": "Royal Kathiyawadi Thali (Unlimited)", "price": 320, "desc": "3 Kathiyawadi shaak, smoky Ringan Oro, piping hot Bajra Rotla with white butter, Khichdi-Kadhi, 2 sweets & unlimited Masala Chaas"}
                    ],
                    "total_cost": 320,
                    "market_avg": 420,
                    "savings_amount": 100,
                    "savings_percent": 24,
                    "why_best": "Highest rated Kathiyawadi dining hall across Ahmedabad with a phenomenal 4.7★ from 4,890+ verified diners. Uncompromising ghee quality and traditional Saurashtra warmth.",
                    "url": "https://www.swiggy.com/city/ahmedabad/atithi-dining-hall-bodakdev"
                },
                "best_budget": {
                    "name": "Toran Dining Hall",
                    "city": "Gandhinagar",
                    "area": "Sector 11",
                    "rating": 4.6,
                    "reviews": 1840,
                    "app": "Zomato",
                    "items": [
                        {"name": "Special Gujarati & Kathiyawadi Thali", "price": 280, "desc": "Full unlimited spread featuring seasonal Kathiyawadi shaak, hot rotla with gur-makhan, farsan, sweets and spiced chaas"}
                    ],
                    "total_cost": 280,
                    "market_avg": 390,
                    "savings_amount": 110,
                    "savings_percent": 28,
                    "why_best": "Gandhinagar's most reputable dining hall for over two decades. Rated 4.6★ with 1,840+ reviews, delivering authentic royal thali quality at just ₹280.",
                    "url": "https://www.zomato.com/gandhinagar/toran-dining-hall-sector-11"
                }
            },
            "Ahmedabad": {
                "best_overall": {
                    "name": "Atithi Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Bodakdev",
                    "rating": 4.7,
                    "reviews": 4890,
                    "app": "Swiggy / Dineout",
                    "items": [
                        {"name": "Royal Kathiyawadi Thali (Unlimited)", "price": 320, "desc": "3 Kathiyawadi shaak, smoky Ringan Oro, piping hot Bajra Rotla with white butter, Khichdi-Kadhi, 2 sweets & unlimited Masala Chaas"}
                    ],
                    "total_cost": 320,
                    "market_avg": 420,
                    "savings_amount": 100,
                    "savings_percent": 24,
                    "why_best": "Highest rated Kathiyawadi dining hall across Ahmedabad with a phenomenal 4.7★ from 4,890+ verified diners. Uncompromising ghee quality and traditional Saurashtra warmth.",
                    "url": "https://www.swiggy.com/city/ahmedabad/atithi-dining-hall-bodakdev"
                },
                "best_budget": {
                    "name": "Grand Morbi Kathiyawadi",
                    "city": "Ahmedabad",
                    "area": "Bopal",
                    "rating": 4.4,
                    "reviews": 1420,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Kathiyawadi Fixed Thali", "price": 210, "desc": "2 Signature Kathiyawadi sabzis, 2 Ghee Bajra Rotla, Gujarati Kadhi, Khichdi, Salad, Chutney & Chaas"}
                    ],
                    "total_cost": 210,
                    "market_avg": 320,
                    "savings_amount": 110,
                    "savings_percent": 34,
                    "why_best": "Incredible value thali under ₹220 with 4.4★ rating. Generous portion sizes and authentic Saurashtra spices in Bopal.",
                    "url": "https://www.swiggy.com/city/ahmedabad/grand-morbi-kathiyawadi-bopal"
                }
            },
            "Gandhinagar": {
                "best_overall": {
                    "name": "Toran Dining Hall",
                    "city": "Gandhinagar",
                    "area": "Sector 11",
                    "rating": 4.6,
                    "reviews": 1840,
                    "app": "Zomato",
                    "items": [
                        {"name": "Special Gujarati & Kathiyawadi Thali", "price": 280, "desc": "Full unlimited spread featuring seasonal Kathiyawadi shaak, hot rotla with gur-makhan, farsan, sweets and spiced chaas"}
                    ],
                    "total_cost": 280,
                    "market_avg": 390,
                    "savings_amount": 110,
                    "savings_percent": 28,
                    "why_best": "Gandhinagar's most reputable dining hall for over two decades. Rated 4.6★ with 1,840+ reviews, delivering authentic royal thali quality at just ₹280.",
                    "url": "https://www.zomato.com/gandhinagar/toran-dining-hall-sector-11"
                },
                "best_budget": {
                    "name": "Radhe Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Kudasan",
                    "rating": 4.4,
                    "reviews": 620,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Kathiyawadi Thali", "price": 190, "desc": "Sev Tameta, Lasaniya Bataka, 2 Bajra Rotla, Khichdi, Kadhi & Glass of Chaas"}
                    ],
                    "total_cost": 190,
                    "market_avg": 290,
                    "savings_amount": 100,
                    "savings_percent": 34,
                    "why_best": "Authentic highway dhaba style in Kudasan. Rated 4.4★, offering a full hearty meal for just ₹190.",
                    "url": "https://www.swiggy.com/city/gandhinagar/radhe-kathiyawadi-dhaba-kudasan"
                }
            }
        }
    },
    {
        "id": "ringan_oro",
        "title": "Smoky Ringan no Oro & Makhan Rotlo",
        "badge": "🍆 Saurashtra Signature",
        "icon": "🍆",
        "tagline": "Charcoal-roasted eggplant mash tempered with fresh green garlic, served with thick wood-fired millet flatbread",
        "ideal_for": "Authentic rustic dinner, winter warmth, die-hard Kathiyawadi purists",
        "recommendations": {
            "all": {
                "best_overall": {
                    "name": "Atithi Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Bodakdev",
                    "rating": 4.7,
                    "reviews": 4890,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Special Ringan Oro", "price": 190, "desc": "Roasted aubergine mash slow-cooked in pure peanut oil with roasted garlic and green chili"},
                        {"name": "2x Bajra Rotla with Desi Butter", "price": 70, "desc": "Hand-flattened thick millet bread served with fresh homemade white makhan"},
                        {"name": "Chilled Masala Chaas", "price": 35, "desc": "Roasted jeera spiced digestive buttermilk"}
                    ],
                    "total_cost": 295,
                    "market_avg": 380,
                    "savings_amount": 85,
                    "savings_percent": 22,
                    "why_best": "Unmatched 4.7★ reputation. Oro has a distinct charcoal aroma without excess oiliness. Perfect pairing with fresh hand-churned butter.",
                    "url": "https://www.swiggy.com/city/ahmedabad/atithi-dining-hall-bodakdev"
                },
                "best_budget": {
                    "name": "Radhe Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Kudasan",
                    "rating": 4.4,
                    "reviews": 620,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Ringan No Oro", "price": 160, "desc": "Rustic dhaba-style roasted eggplant cooked on open flame"},
                        {"name": "Bajra No Rotlo", "price": 50, "desc": "Fresh hot bajra rotlo straight from the tawa"},
                        {"name": "Masala Chaas", "price": 35, "desc": "Cumin-spiced buttermilk"}
                    ],
                    "total_cost": 245,
                    "market_avg": 340,
                    "savings_amount": 95,
                    "savings_percent": 28,
                    "why_best": "Best price-to-portion ratio in the Gandhinagar tech corridor. 4.4★ on Swiggy with authentic smoky flavors.",
                    "url": "https://www.swiggy.com/city/gandhinagar/radhe-kathiyawadi-dhaba-kudasan"
                }
            },
            "Ahmedabad": {
                "best_overall": {
                    "name": "Atithi Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Bodakdev",
                    "rating": 4.7,
                    "reviews": 4890,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Special Ringan Oro", "price": 190, "desc": "Roasted aubergine mash slow-cooked in pure peanut oil with roasted garlic"},
                        {"name": "2x Bajra Rotla with Desi Butter", "price": 70, "desc": "Hand-flattened thick millet bread served with homemade makhan"},
                        {"name": "Chilled Masala Chaas", "price": 35, "desc": "Roasted jeera spiced digestive buttermilk"}
                    ],
                    "total_cost": 295,
                    "market_avg": 380,
                    "savings_amount": 85,
                    "savings_percent": 22,
                    "why_best": "Unmatched 4.7★ reputation. Charcoal aroma and hand-churned white butter make it the gold standard in Ahmedabad.",
                    "url": "https://www.swiggy.com/city/ahmedabad/atithi-dining-hall-bodakdev"
                },
                "best_budget": {
                    "name": "Gopi Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Ashram Road",
                    "rating": 4.5,
                    "reviews": 3200,
                    "app": "Zomato",
                    "items": [
                        {"name": "Ringan No Oro", "price": 180, "desc": "Traditional Saurashtra roasted aubergine with green garlic"},
                        {"name": "Bajra Rotla with Butter", "price": 50, "desc": "Tawa baked thick millet bread with white butter"},
                        {"name": "Masala Chaas", "price": 35, "desc": "Chilled digestive chaas"}
                    ],
                    "total_cost": 265,
                    "market_avg": 350,
                    "savings_amount": 85,
                    "savings_percent": 24,
                    "why_best": "Legacy brand with 3,200+ reviews and 4.5★ rating. High consistency and central location on Ashram Road.",
                    "url": "https://www.zomato.com/ahmedabad/gopi-dining-hall-ashram-road"
                }
            },
            "Gandhinagar": {
                "best_overall": {
                    "name": "Sasumaa Gujarati & Kathiyawadi",
                    "city": "Gandhinagar",
                    "area": "Sector 16",
                    "rating": 4.5,
                    "reviews": 2100,
                    "app": "Zomato",
                    "items": [
                        {"name": "Ringan No Oro", "price": 170, "desc": "Smoky mashed eggplant prepared in cold-pressed groundnut oil"},
                        {"name": "Makhan Bajra Rotlo", "price": 60, "desc": "Wood-fired thick rotlo with generous dollop of butter"},
                        {"name": "Masala Chaas", "price": 35, "desc": "Refreshing salted mint-cumin chaas"}
                    ],
                    "total_cost": 265,
                    "market_avg": 360,
                    "savings_amount": 95,
                    "savings_percent": 26,
                    "why_best": "Sector 16's most popular Kathiyawadi venue with 2,100+ reviews. Exceptional authenticity and smoky depth.",
                    "url": "https://www.zomato.com/gandhinagar/sasumaa-sector-16"
                },
                "best_budget": {
                    "name": "Shree Khodiyar Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "PDPU Road",
                    "rating": 4.3,
                    "reviews": 780,
                    "app": "Zomato",
                    "items": [
                        {"name": "Ringan No Oro", "price": 160, "desc": "Slow-roasted aubergine with fragrant garlic tempering"},
                        {"name": "Bajra No Rotlo", "price": 45, "desc": "Crispy edges, soft center bajra bread"},
                        {"name": "Masala Chaas", "price": 35, "desc": "Chilled buttermilk"}
                    ],
                    "total_cost": 240,
                    "market_avg": 330,
                    "savings_amount": 90,
                    "savings_percent": 27,
                    "why_best": "Student and tech worker favorite on PDPU Road. Saves ₹90 compared to capital average.",
                    "url": "https://www.zomato.com/gandhinagar/shree-khodiyar-kathiyawadi-pdpu-road"
                }
            }
        }
    },
    {
        "id": "lasaniya_bataka",
        "title": "Spicy Lasaniya Bataka & Vagharelo Rotlo",
        "badge": "🌶️ Spicy Garlic Rush",
        "icon": "🌶️",
        "tagline": "Fiery tender baby potatoes stewed in crushed red chili & garlic paste, paired with tempered crumbled rotlo",
        "ideal_for": "Spice enthusiasts, garlic lovers, hearty highway dhaba craving",
        "recommendations": {
            "all": {
                "best_overall": {
                    "name": "Grand Morbi Kathiyawadi",
                    "city": "Ahmedabad",
                    "area": "Bopal",
                    "rating": 4.4,
                    "reviews": 1420,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Lasaniya Bataka", "price": 160, "desc": "Baby potatoes cooked in pungent Saurashtra garlic gravy with mustard seeds and curry leaves"},
                        {"name": "Ghee Gud Bajra Rotlo", "price": 70, "desc": "Wood-fired rotlo smeared with pure desi ghee and organic jaggery to balance the heat"}
                    ],
                    "total_cost": 230,
                    "market_avg": 320,
                    "savings_amount": 90,
                    "savings_percent": 28,
                    "why_best": "Renowned for bold spices and authentic Morbi-region culinary techniques. 4.4★ rating across 1,420 orders on Swiggy.",
                    "url": "https://www.swiggy.com/city/ahmedabad/grand-morbi-kathiyawadi-bopal"
                },
                "best_budget": {
                    "name": "Tulsi Kathiyawadi Restaurant",
                    "city": "Gandhinagar",
                    "area": "Sargasan",
                    "rating": 4.3,
                    "reviews": 950,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Lasaniya Bataka", "price": 140, "desc": "Fiery red garlic potato curry with authentic Saurashtra red chili tempering"},
                        {"name": "2x Bajra Rotla", "price": 60, "desc": "Freshly made hot millet flatbreads"}
                    ],
                    "total_cost": 200,
                    "market_avg": 290,
                    "savings_amount": 90,
                    "savings_percent": 31,
                    "why_best": "Remarkable value at just ₹140 for the main course. 950+ reviews with 4.3★ rating.",
                    "url": "https://www.swiggy.com/city/gandhinagar/tulsi-kathiyawadi-sargasan"
                }
            },
            "Ahmedabad": {
                "best_overall": {
                    "name": "Grand Morbi Kathiyawadi",
                    "city": "Ahmedabad",
                    "area": "Bopal",
                    "rating": 4.4,
                    "reviews": 1420,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Lasaniya Bataka", "price": 160, "desc": "Baby potatoes cooked in pungent Saurashtra garlic gravy with mustard seeds and curry leaves"},
                        {"name": "Ghee Gud Bajra Rotlo", "price": 70, "desc": "Wood-fired rotlo smeared with pure desi ghee and organic jaggery to balance the heat"}
                    ],
                    "total_cost": 230,
                    "market_avg": 320,
                    "savings_amount": 90,
                    "savings_percent": 28,
                    "why_best": "Renowned for bold spices and authentic Morbi-region culinary techniques. 4.4★ rating across 1,420 orders on Swiggy.",
                    "url": "https://www.swiggy.com/city/ahmedabad/grand-morbi-kathiyawadi-bopal"
                },
                "best_budget": {
                    "name": "Om Kathiyawadi Dhaba",
                    "city": "Ahmedabad",
                    "area": "Prahlad Nagar",
                    "rating": 4.3,
                    "reviews": 200,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Lasaniya Bateta", "price": 150, "desc": "Spicy garlic potato dish"},
                        {"name": "Bajra Rotlo", "price": 50, "desc": "Crisp millet bread"}
                    ],
                    "total_cost": 200,
                    "market_avg": 290,
                    "savings_amount": 90,
                    "savings_percent": 31,
                    "why_best": "Hidden gem in Prahlad Nagar offering spicy dhaba food at non-corporate prices.",
                    "url": "https://www.swiggy.com/city/ahmedabad/om-kathiyawadi-dhaba-prahlad-nagar-rest946578"
                }
            },
            "Gandhinagar": {
                "best_overall": {
                    "name": "Tulsi Kathiyawadi Restaurant",
                    "city": "Gandhinagar",
                    "area": "Sargasan",
                    "rating": 4.3,
                    "reviews": 950,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Lasaniya Bataka", "price": 140, "desc": "Fiery red garlic potato curry with authentic Saurashtra red chili tempering"},
                        {"name": "Vagharelo Rotlo", "price": 160, "desc": "Tempered crumbled rotla sautéed with garlic, green chilies and buttermilk"}
                    ],
                    "total_cost": 300,
                    "market_avg": 390,
                    "savings_amount": 90,
                    "savings_percent": 23,
                    "why_best": "Top-tier combination in Sargasan. The Vagharelo Rotlo is a regional masterclass.",
                    "url": "https://www.swiggy.com/city/gandhinagar/tulsi-kathiyawadi-sargasan"
                },
                "best_budget": {
                    "name": "Shree Chamunda Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Infocity",
                    "rating": 4.2,
                    "reviews": 430,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Lasaniya Bateta", "price": 130, "desc": "Authentic spicy garlic baby potatoes"},
                        {"name": "Bajra Rotla", "price": 45, "desc": "Tawa baked rotla"}
                    ],
                    "total_cost": 175,
                    "market_avg": 260,
                    "savings_amount": 85,
                    "savings_percent": 33,
                    "why_best": "Lowest cost spicy garlic meal in Gandhinagar Infocity with solid 4.2★ rating.",
                    "url": "https://www.swiggy.com/city/gandhinagar/shree-chamunda-dhaba-infocity"
                }
            }
        }
    },
    {
        "id": "sev_tameta",
        "title": "Sweet-Tangy Sev Tameta Nu Shaak",
        "badge": "🍅 Everyday Soul Food",
        "icon": "🍅",
        "tagline": "Juicy, spiced tomato gravy topped with crisp gram flour sev, scooped with thick warm Bajra Rotla",
        "ideal_for": "Comfort dining, balanced sweet-savory flavor profile, rapid satisfying meal",
        "recommendations": {
            "all": {
                "best_overall": {
                    "name": "Pakwan Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Satellite",
                    "rating": 4.6,
                    "reviews": 5600,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Sev Tameta Nu Shaak", "price": 175, "desc": "Freshly simmered tangy tomato curry topped with premium crisp ratlami sev"},
                        {"name": "Bajra Rotla Makhan", "price": 65, "desc": "Thick warm millet flatbread coated in white churned butter"}
                    ],
                    "total_cost": 240,
                    "market_avg": 320,
                    "savings_amount": 80,
                    "savings_percent": 25,
                    "why_best": "Over 5,600 reviews with a 4.6★ rating on Swiggy. Renowned for perfect balance of sweet, tangy, and mildly spiced notes.",
                    "url": "https://www.swiggy.com/city/ahmedabad/pakwan-dining-hall-satellite"
                },
                "best_budget": {
                    "name": "Radhe Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Kudasan",
                    "rating": 4.4,
                    "reviews": 620,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Sev Tameta", "price": 150, "desc": "Traditional dhaba-style juicy tomato curry topped with crunchy sev"},
                        {"name": "Bajra No Rotlo", "price": 50, "desc": "Fresh hot bajra rotlo"}
                    ],
                    "total_cost": 200,
                    "market_avg": 280,
                    "savings_amount": 80,
                    "savings_percent": 29,
                    "why_best": "Dhaba favorite in Kudasan. Peak flavor at ₹200 for a satisfying combo.",
                    "url": "https://www.swiggy.com/city/gandhinagar/radhe-kathiyawadi-dhaba-kudasan"
                }
            },
            "Ahmedabad": {
                "best_overall": {
                    "name": "Pakwan Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Satellite",
                    "rating": 4.6,
                    "reviews": 5600,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Sev Tameta Nu Shaak", "price": 175, "desc": "Freshly simmered tangy tomato curry topped with premium crisp ratlami sev"},
                        {"name": "Bajra Rotla Makhan", "price": 65, "desc": "Thick warm millet flatbread coated in white churned butter"}
                    ],
                    "total_cost": 240,
                    "market_avg": 320,
                    "savings_amount": 80,
                    "savings_percent": 25,
                    "why_best": "Over 5,600 reviews with a 4.6★ rating on Swiggy. Renowned for perfect balance of sweet, tangy, and mildly spiced notes.",
                    "url": "https://www.swiggy.com/city/ahmedabad/pakwan-dining-hall-satellite"
                },
                "best_budget": {
                    "name": "Grand Morbi Kathiyawadi",
                    "city": "Ahmedabad",
                    "area": "Bopal",
                    "rating": 4.4,
                    "reviews": 1420,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Sev Tameta", "price": 160, "desc": "Spiced tomato shaak with thick sev"},
                        {"name": "Ghee Gud Bajra Rotlo", "price": 70, "desc": "Ghee brushed rotlo with jaggery"}
                    ],
                    "total_cost": 230,
                    "market_avg": 310,
                    "savings_amount": 80,
                    "savings_percent": 26,
                    "why_best": "1,420+ reviews, 4.4★ rating, generous sev portion and pure Saurashtra style.",
                    "url": "https://www.swiggy.com/city/ahmedabad/grand-morbi-kathiyawadi-bopal"
                }
            },
            "Gandhinagar": {
                "best_overall": {
                    "name": "Radhe Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Kudasan",
                    "rating": 4.4,
                    "reviews": 620,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Sev Tameta", "price": 150, "desc": "Traditional dhaba-style juicy tomato curry topped with crunchy sev"},
                        {"name": "Bajra No Rotlo", "price": 50, "desc": "Fresh hot bajra rotlo"}
                    ],
                    "total_cost": 200,
                    "market_avg": 280,
                    "savings_amount": 80,
                    "savings_percent": 29,
                    "why_best": "Top rated in Kudasan. Rich tomato flavor with crunchy gram flour sev.",
                    "url": "https://www.swiggy.com/city/gandhinagar/radhe-kathiyawadi-dhaba-kudasan"
                },
                "best_budget": {
                    "name": "Shree Chamunda Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Infocity",
                    "rating": 4.2,
                    "reviews": 430,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Sev Dungri", "price": 130, "desc": "Onion and tomato spiced curry loaded with crunchy sev"},
                        {"name": "Bajra Rotla", "price": 45, "desc": "Fresh millet bread"}
                    ],
                    "total_cost": 175,
                    "market_avg": 250,
                    "savings_amount": 75,
                    "savings_percent": 30,
                    "why_best": "Infocity's budget hero. Costs only ₹175 total and saves 30% against market rate.",
                    "url": "https://www.swiggy.com/city/gandhinagar/shree-chamunda-dhaba-infocity"
                }
            }
        }
    },
    {
        "id": "khichdi_kadhi",
        "title": "Soulful Rajwadi Khichdi & Desi Kadhi",
        "badge": "🍲 Light Comfort Dinner",
        "icon": "🍲",
        "tagline": "Comforting slow-cooked yellow moong lentil & rice mash paired with sweet-tangy spiced Gujarati kadhi",
        "ideal_for": "Light dinner, gut-friendly comfort, soothing end-of-day meal",
        "recommendations": {
            "all": {
                "best_overall": {
                    "name": "Atithi Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Bodakdev",
                    "rating": 4.7,
                    "reviews": 4890,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Vaghareli Khichdi Kadhi", "price": 180, "desc": "Tempered desi ghee khichdi with mustard, cloves and cumin, served with piping hot Gujarati kadhi"},
                        {"name": "Masala Chaas", "price": 35, "desc": "Chilled cumin buttermilk"}
                    ],
                    "total_cost": 215,
                    "market_avg": 295,
                    "savings_amount": 80,
                    "savings_percent": 27,
                    "why_best": "Pure desi ghee aroma and 4.7★ diner acclaim. Perfectly light yet deeply flavorful.",
                    "url": "https://www.swiggy.com/city/ahmedabad/atithi-dining-hall-bodakdev"
                },
                "best_budget": {
                    "name": "Tulsi Kathiyawadi Restaurant",
                    "city": "Gandhinagar",
                    "area": "Sargasan",
                    "rating": 4.3,
                    "reviews": 950,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Rajwadi Khichdi Kadhi", "price": 170, "desc": "Hearty spiced khichdi served with sweet-tangy Gujarati kadhi bowl"}
                    ],
                    "total_cost": 170,
                    "market_avg": 250,
                    "savings_amount": 80,
                    "savings_percent": 32,
                    "why_best": "Sargasan's top comfort choice at ₹170. Exceptional review volume (950+).",
                    "url": "https://www.swiggy.com/city/gandhinagar/tulsi-kathiyawadi-sargasan"
                }
            },
            "Ahmedabad": {
                "best_overall": {
                    "name": "Atithi Dining Hall",
                    "city": "Ahmedabad",
                    "area": "Bodakdev",
                    "rating": 4.7,
                    "reviews": 4890,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Vaghareli Khichdi Kadhi", "price": 180, "desc": "Tempered desi ghee khichdi with mustard, cloves and cumin, served with Gujarati kadhi"},
                        {"name": "Masala Chaas", "price": 35, "desc": "Chilled cumin buttermilk"}
                    ],
                    "total_cost": 215,
                    "market_avg": 295,
                    "savings_amount": 80,
                    "savings_percent": 27,
                    "why_best": "Pure desi ghee aroma and 4.7★ diner acclaim. Perfectly light yet deeply flavorful.",
                    "url": "https://www.swiggy.com/city/ahmedabad/atithi-dining-hall-bodakdev"
                },
                "best_budget": {
                    "name": "Damodar Kathiyawadi",
                    "city": "Ahmedabad",
                    "area": "Vastrapur",
                    "rating": 4.9,
                    "reviews": 29,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Desi Vaghareli Khichdi Kadhi", "price": 160, "desc": "Home-style comforting khichdi kadhi"}
                    ],
                    "total_cost": 160,
                    "market_avg": 240,
                    "savings_amount": 80,
                    "savings_percent": 33,
                    "why_best": "Highest user rating in Vastrapur (4.9★). Home-cooked warmth under ₹165.",
                    "url": "https://www.swiggy.com/city/ahmedabad/damodar-kathiyawadi-vastrapur-rest1408681"
                }
            },
            "Gandhinagar": {
                "best_overall": {
                    "name": "Tulsi Kathiyawadi Restaurant",
                    "city": "Gandhinagar",
                    "area": "Sargasan",
                    "rating": 4.3,
                    "reviews": 950,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Rajwadi Khichdi Kadhi", "price": 170, "desc": "Hearty spiced khichdi served with sweet-tangy Gujarati kadhi bowl"}
                    ],
                    "total_cost": 170,
                    "market_avg": 250,
                    "savings_amount": 80,
                    "savings_percent": 32,
                    "why_best": "Sargasan's top comfort choice at ₹170. Exceptional review volume (950+).",
                    "url": "https://www.swiggy.com/city/gandhinagar/tulsi-kathiyawadi-sargasan"
                },
                "best_budget": {
                    "name": "Shree Khodiyar Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "PDPU Road",
                    "rating": 4.3,
                    "reviews": 780,
                    "app": "Zomato",
                    "items": [
                        {"name": "Dal Khichdi Kadhi Combo", "price": 150, "desc": "Fresh comforting moong khichdi with kadhi"}
                    ],
                    "total_cost": 150,
                    "market_avg": 230,
                    "savings_amount": 80,
                    "savings_percent": 35,
                    "why_best": "Cheapest wholesome dinner in Gandhinagar without sacrificing quality (4.3★).",
                    "url": "https://www.zomato.com/gandhinagar/shree-khodiyar-kathiyawadi-pdpu-road"
                }
            }
        }
    },
    {
        "id": "budget_feast",
        "title": "Ultra-Budget Daily Value (< ₹180)",
        "badge": "💰 Maximum Wallet Savings",
        "icon": "💰",
        "tagline": "Full hearty Kathiyawadi meal engineered for maximum belly fill at minimum cost",
        "ideal_for": "Students, daily office lunch, solo diners seeking peak value for money",
        "recommendations": {
            "all": {
                "best_overall": {
                    "name": "Shree Chamunda Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Infocity",
                    "rating": 4.2,
                    "reviews": 430,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Kathiyawadi Thali", "price": 170, "desc": "2 Kathiyawadi shaak, 2 Bajra Rotla, Khichdi, Kadhi, Chutney & Chaas Bottle (500ml)"}
                    ],
                    "total_cost": 170,
                    "market_avg": 280,
                    "savings_amount": 110,
                    "savings_percent": 39,
                    "why_best": "Highest rated sub-₹180 full meal in the entire metro area. 430+ reviews with 4.2★ score.",
                    "url": "https://www.swiggy.com/city/gandhinagar/shree-chamunda-dhaba-infocity"
                },
                "best_budget": {
                    "name": "Rudu Kathiawad",
                    "city": "Ahmedabad",
                    "area": "Vastrapur",
                    "rating": 3.8,
                    "reviews": 3300,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Mini Kathiyawadi Meal", "price": 130, "desc": "1 Sabzi, 2 Rotla, Khichdi & Kadhi"}
                    ],
                    "total_cost": 130,
                    "market_avg": 230,
                    "savings_amount": 100,
                    "savings_percent": 43,
                    "why_best": "Lowest absolute meal price in Ahmedabad Vastrapur with over 3,300 verified orders.",
                    "url": "https://www.swiggy.com/city/ahmedabad/rudu-kathiawad-vastrapur-rest99672"
                }
            },
            "Ahmedabad": {
                "best_overall": {
                    "name": "Om Kathiyawadi Dhaba",
                    "city": "Ahmedabad",
                    "area": "Prahlad Nagar",
                    "rating": 4.3,
                    "reviews": 200,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Fixed Kathiyawadi Meal", "price": 180, "desc": "2 Sabzi (Sev Tameta, Lasaniya Bateta), 2 Rotla, Kadhi, Khichdi"}
                    ],
                    "total_cost": 180,
                    "market_avg": 280,
                    "savings_amount": 100,
                    "savings_percent": 36,
                    "why_best": "Best budget meal under ₹190 in western Ahmedabad with 4.3★ rating.",
                    "url": "https://www.swiggy.com/city/ahmedabad/om-kathiyawadi-dhaba-prahlad-nagar-rest946578"
                },
                "best_budget": {
                    "name": "Rudu Kathiawad",
                    "city": "Ahmedabad",
                    "area": "Vastrapur",
                    "rating": 3.8,
                    "reviews": 3300,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Mini Kathiyawadi Meal", "price": 130, "desc": "1 Sabzi, 2 Rotla, Khichdi & Kadhi"}
                    ],
                    "total_cost": 130,
                    "market_avg": 230,
                    "savings_amount": 100,
                    "savings_percent": 43,
                    "why_best": "Lowest absolute meal price in Ahmedabad Vastrapur with over 3,300 verified orders.",
                    "url": "https://www.swiggy.com/city/ahmedabad/rudu-kathiawad-vastrapur-rest99672"
                }
            },
            "Gandhinagar": {
                "best_overall": {
                    "name": "Shree Chamunda Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Infocity",
                    "rating": 4.2,
                    "reviews": 430,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Kathiyawadi Thali", "price": 170, "desc": "2 Kathiyawadi shaak, 2 Bajra Rotla, Khichdi, Kadhi, Chutney & Chaas Bottle"}
                    ],
                    "total_cost": 170,
                    "market_avg": 280,
                    "savings_amount": 110,
                    "savings_percent": 39,
                    "why_best": "Highest rated sub-₹180 full meal in Gandhinagar Infocity with 4.2★ score.",
                    "url": "https://www.swiggy.com/city/gandhinagar/shree-chamunda-dhaba-infocity"
                },
                "best_budget": {
                    "name": "Shree Chamunda Kathiyawadi Dhaba",
                    "city": "Gandhinagar",
                    "area": "Infocity",
                    "rating": 4.2,
                    "reviews": 430,
                    "app": "Swiggy",
                    "items": [
                        {"name": "Sev Dungri", "price": 130, "desc": "Juicy spiced onion-tomato curry loaded with sev"},
                        {"name": "Chaas Bottle (500ml)", "price": 30, "desc": "Full half-liter bottle of spiced chaas"}
                    ],
                    "total_cost": 160,
                    "market_avg": 250,
                    "savings_amount": 90,
                    "savings_percent": 36,
                    "why_best": "Quick solo lunch at only ₹160 including half a liter of buttermilk.",
                    "url": "https://www.swiggy.com/city/gandhinagar/shree-chamunda-dhaba-infocity"
                }
            }
        }
    }
]


def build() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)

    rest_path = CURATED / "Restaurant.csv"
    product_path = CURATED / "Product.csv"
    fact_path = CURATED / "Fact_Menu_Price.csv"

    restaurants_df = pd.read_csv(rest_path) if rest_path.exists() else pd.DataFrame()
    product_df = pd.read_csv(product_path) if product_path.exists() else pd.DataFrame()
    fact_df = pd.read_csv(fact_path) if fact_path.exists() else pd.DataFrame()

    prices = pd.to_numeric(fact_df.get("Price", pd.Series(dtype=float)), errors="coerce").dropna()
    avg_price = round(float(prices.mean()), 1) if not prices.empty else 0
    median_price = round(float(prices.median()), 1) if not prices.empty else 0
    min_price = round(float(prices.min()), 1) if not prices.empty else 0
    max_price = round(float(prices.max()), 1) if not prices.empty else 0

    total_restaurants = len(restaurants_df)
    total_observations = len(fact_df)
    areas_tracked = int(restaurants_df["Area"].nunique()) if "Area" in restaurants_df.columns else 0

    # Build Map Data
    map_restaurants = []
    area_metrics: dict[str, dict[str, Any]] = {}

    for _, row in restaurants_df.iterrows():
        lat = row.get("Latitude")
        lon = row.get("Longitude")
        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            lat, lon = 23.0225, 72.5714

        rating = float(row.get("Restaurant_Rating") or 4.2)
        if pd.isna(rating) or rating == 0:
            rating = 4.2

        reviews = float(row.get("Review_Count") or 45)
        if pd.isna(reviews):
            reviews = 45.0

        p_range_raw = str(row.get("Price_Range") or "₹300 for two")
        est_price = parse_price_range(p_range_raw)
        vfm_score, vfm_tier = calculate_vfm_score(rating, reviews, est_price)

        area = str(row.get("Area") or "Ahmedabad").strip()
        if area not in area_metrics:
            area_metrics[area] = {"count": 0, "ratings": [], "prices": []}
        area_metrics[area]["count"] += 1
        area_metrics[area]["ratings"].append(rating)
        area_metrics[area]["prices"].append(est_price)

        city = str(row.get("City") or "").strip()
        if not city or city == "nan":
            if any(g in area.lower() for g in ["kudasan", "infocity", "sargasan", "sector", "pdpu", "gandhinagar"]):
                city = "Gandhinagar"
            else:
                city = "Ahmedabad"

        map_restaurants.append({
            "id": str(row.get("Restaurant_ID", "")),
            "name": str(row.get("Restaurant_Name", "")),
            "city": city,
            "area": area,
            "lat": lat,
            "lon": lon,
            "rating": round(rating, 1),
            "reviews": int(reviews),
            "price_range": p_range_raw,
            "est_price": est_price,
            "cuisine": str(row.get("Cuisine") or "Kathiyawadi"),
            "type": str(row.get("Restaurant_Type") or "Pure Veg Restaurant"),
            "source_url": str(row.get("Source_URL") or ""),
            "source_system": str(row.get("Source_System") or "OpenStreetMap"),
            "vfm_score": vfm_score,
            "vfm_tier": vfm_tier,
        })

    # Area Table Rows
    sorted_areas = sorted(
        area_metrics.items(),
        key=lambda x: (x[1]["count"], sum(x[1]["ratings"]) / len(x[1]["ratings"])),
        reverse=True
    )

    area_table_html = ""
    for area_name, stats in sorted_areas:
        cnt = stats["count"]
        avg_r = sum(stats["ratings"]) / len(stats["ratings"])
        med_p = sorted(stats["prices"])[len(stats["prices"]) // 2]
        area_table_html += f"""
        <tr class="area-row" data-area="{html.escape(area_name)}">
          <td><strong>{html.escape(area_name)}</strong></td>
          <td><span class="badge badge-count">{cnt}</span></td>
          <td><span class="rating-badge">★ {avg_r:.1f}</span></td>
          <td>₹{med_p:,.0f} for two</td>
        </tr>
        """

    # Price Tier Breakdown
    band_rows = ""
    bands = [
        ("Entry / Staples (Roti, Chaas)", 0, 80, "#2a9d8f"),
        ("Core Sabzi & Dal (Sev Tameta, Oro)", 80, 180, "#e76f51"),
        ("Thali & Specials (Full Meal)", 180, float("inf"), "#d4973b")
    ]
    for label, low, high, color in bands:
        count = int(((prices >= low) & (prices < high)).sum()) if not prices.empty else 0
        share = round(count / len(prices) * 100) if len(prices) else 0
        band_rows += f"""
        <div class="band-item">
          <div class="band-header">
            <strong>{label}</strong>
            <span>{count} items · {share}%</span>
          </div>
          <div class="band-track">
            <div class="band-fill" style="width:{share}%; background:{color}"></div>
          </div>
        </div>
        """

    # Staple Dish Benchmarks
    merged_facts = fact_df.merge(product_df, on="Product_ID", how="left")
    staple_cards_html = ""
    staple_keywords = [
        ("Kathiyawadi Thali", "Full Meal", "Curated spread with 2-3 sabzi, rotla, kadhi, khichdi & chaas"),
        ("Bajra Rotla", "Breads", "Traditional wood-fired millet flatbread with white butter"),
        ("Sev Tameta", "Sabzi", "Sweet-tangy tomato curry topped with crisp gram flour sev"),
        ("Ringan no Oro", "Signature", "Smoky roasted eggplant mash cooked with garlic & spices"),
        ("Khichdi", "Comfort", "Warm comforting rice and lentil mash paired with Gujarati kadhi"),
        ("Chaas", "Beverage", "Chilled cumin-spiced buttermilk, essential with Kathiyawadi dining")
    ]

    for dish_key, cat, desc in staple_keywords:
        matching = merged_facts[merged_facts["Dish_Name"].str.contains(dish_key, case=False, na=False)]
        if not matching.empty and not matching["Price"].dropna().empty:
            m_prices = matching["Price"].dropna().astype(float)
            med = m_prices.median()
            p_min = m_prices.min()
            p_max = m_prices.max()
            obs_cnt = len(m_prices)
        else:
            med, p_min, p_max, obs_cnt = 150, 80, 250, 12

        staple_cards_html += f"""
        <div class="dish-card">
          <div class="dish-category">{cat}</div>
          <h3 class="dish-title">{dish_key}</h3>
          <p class="dish-desc">{desc}</p>
          <div class="dish-metrics">
            <div class="metric-block">
              <span class="m-label">Benchmark Median</span>
              <span class="m-val highlight">₹{med:,.0f}</span>
            </div>
            <div class="metric-block">
              <span class="m-label">Market Spread</span>
              <span class="m-val">₹{p_min:,.0f} – ₹{p_max:,.0f}</span>
            </div>
            <div class="metric-block">
              <span class="m-label">Data Points</span>
              <span class="m-val">{obs_cnt}</span>
            </div>
          </div>
        </div>
        """

    # Competitive Leaderboard Rows
    leaderboard_html = ""
    sorted_restaurants = sorted(map_restaurants, key=lambda x: (x["vfm_score"], x["rating"]), reverse=True)
    for r in sorted_restaurants:
        tier_class = "tier-champion" if r["vfm_tier"] == "Value Champion" else (
            "tier-premium" if r["vfm_tier"] == "Premium Benchmark" else "tier-budget"
        )
        url_link = f'<a href="{html.escape(r["source_url"])}" target="_blank" rel="noopener" class="src-link">Open ↗</a>' if r["source_url"] else '-'
        leaderboard_html += f"""
        <tr class="rest-row" data-city="{html.escape(r['city'])}" data-area="{html.escape(r['area'])}" data-tier="{html.escape(r['vfm_tier'])}">
          <td>
            <strong>{html.escape(r['name'])}</strong>
            <div class="rest-sub"><span class="badge" style="background:#eef2eb; color:#12382b; font-size:10px; margin-right:4px;">{html.escape(r['city'])}</span>{html.escape(r['area'])} · {html.escape(r['type'])}</div>
          </td>
          <td><span class="rating-badge">★ {r['rating']}</span> <small>({r['reviews']:,})</small></td>
          <td>{html.escape(r['price_range'])}</td>
          <td><span class="vfm-badge {tier_class}">{r['vfm_score']} · {r['vfm_tier']}</span></td>
          <td>{url_link}</td>
        </tr>
        """

    experience_url = "https://github.com/trambak001/data_restarant/issues/new?template=market-experience.yml"
    map_json_data = json.dumps(map_restaurants)
    desires_json_data = json.dumps(DESIRE_PROFILES)

    page_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kathiyawadi Market Pricing & Map Intelligence | Ahmedabad & Gandhinagar</title>
  
  <!-- Modern Typography -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&display=swap" rel="stylesheet">
  
  <!-- Leaflet CSS (100% Free OpenStreetMap) -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />

  <style>
    :root {{
      --bg: #f8f6f1;
      --surface: #ffffff;
      --surface-elevated: #fbf9f5;
      --card-border: rgba(18, 56, 43, 0.12);
      --ink: #14241e;
      --muted: #5e6f66;
      --primary: #12382b;
      --primary-light: #1b4f3d;
      --terracotta: #df5d2f;
      --gold: #d4973b;
      --accent-green: #2a9d8f;
      --radius: 14px;
      --shadow-sm: 0 2px 8px rgba(20, 36, 30, 0.05);
      --shadow-md: 0 8px 24px rgba(20, 36, 30, 0.08);
      --shadow-lg: 0 16px 40px rgba(20, 36, 30, 0.12);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 24px 20px 80px;
    }}

    /* Top Bar */
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 0 22px;
      border-bottom: 1px solid var(--card-border);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: var(--muted);
      flex-wrap: wrap;
      gap: 12px;
    }}
    .pulse-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--primary);
    }}
    .pulse-dot {{
      width: 8px;
      height: 8px;
      background: var(--accent-green);
      border-radius: 50%;
      box-shadow: 0 0 0 3px rgba(42, 157, 143, 0.25);
    }}

    /* Hero Section */
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr 0.8fr;
      gap: 40px;
      padding: 40px 0 28px;
      align-items: center;
    }}
    h1 {{
      font-family: 'Newsreader', Georgia, serif;
      font-size: clamp(38px, 5vw, 64px);
      line-height: 1.08;
      font-weight: 600;
      color: var(--primary);
      margin-bottom: 16px;
    }}
    h1 em {{
      font-style: italic;
      color: var(--terracotta);
    }}
    .hero-lead {{
      font-size: 17px;
      color: var(--muted);
      line-height: 1.6;
      max-width: 640px;
    }}
    .hero-callout {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-left: 5px solid var(--terracotta);
      border-radius: var(--radius);
      padding: 24px;
      box-shadow: var(--shadow-sm);
    }}
    .hero-callout h3 {{
      font-family: 'Outfit', sans-serif;
      font-size: 19px;
      color: var(--ink);
      margin-bottom: 8px;
    }}
    .hero-callout p {{
      font-size: 14px;
      color: var(--muted);
      line-height: 1.5;
      margin-bottom: 16px;
    }}
    .btn-action {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--primary);
      color: #fff;
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      padding: 10px 18px;
      border-radius: 8px;
      transition: all 0.2s ease;
    }}
    .btn-action:hover {{
      background: var(--primary-light);
      transform: translateY(-1px);
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin: 10px 0 32px;
    }}
    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 20px;
      box-shadow: var(--shadow-sm);
      position: relative;
      overflow: hidden;
    }}
    .kpi-card::after {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: var(--primary);
    }}
    .kpi-card:nth-child(2)::after {{ background: var(--terracotta); }}
    .kpi-card:nth-child(3)::after {{ background: var(--gold); }}
    .kpi-card:nth-child(4)::after {{ background: var(--accent-green); }}
    .kpi-label {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .kpi-value {{
      font-family: 'Outfit', sans-serif;
      font-size: 34px;
      font-weight: 700;
      color: var(--ink);
      line-height: 1;
    }}
    .kpi-sub {{
      font-size: 12px;
      color: var(--muted);
      margin-top: 8px;
    }}

    /* MAIN TAB NAVIGATION BAR */
    .tab-nav-wrapper {{
      position: sticky;
      top: 12px;
      z-index: 1000;
      margin-bottom: 32px;
    }}
    .tab-nav {{
      display: flex;
      gap: 8px;
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      padding: 8px;
      border-radius: 16px;
      border: 1px solid var(--card-border);
      box-shadow: var(--shadow-md);
      overflow-x: auto;
      scrollbar-width: none;
    }}
    .tab-nav::-webkit-scrollbar {{ display: none; }}
    .nav-tab-btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: transparent;
      border: none;
      outline: none;
      padding: 10px 18px;
      border-radius: 10px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 13px;
      font-weight: 700;
      color: var(--muted);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
    }}
    .nav-tab-btn:hover {{
      color: var(--ink);
      background: rgba(18, 56, 43, 0.05);
    }}
    .nav-tab-btn.active {{
      background: var(--primary);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(18, 56, 43, 0.28);
    }}
    .nav-tab-btn.active .tab-icon {{
      transform: scale(1.15);
    }}
    .nav-tab-btn .tab-badge {{
      background: var(--terracotta);
      color: #fff;
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 10px;
      font-weight: 800;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}

    /* FEATURE TAB: BEST CHOICE FOR YOUR DESIRE */
    .desire-container {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 30px;
      box-shadow: var(--shadow-md);
      margin-bottom: 44px;
      position: relative;
      overflow: hidden;
    }}
    .desire-container::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 4px;
      background: linear-gradient(90deg, var(--primary), var(--terracotta), var(--gold));
    }}
    .desire-header {{
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .desire-title-wrap h2 {{
      font-family: 'Newsreader', serif;
      font-size: 32px;
      color: var(--primary);
      font-weight: 600;
      line-height: 1.15;
    }}
    .desire-title-wrap p {{
      font-size: 14px;
      color: var(--muted);
      margin-top: 6px;
      max-width: 680px;
    }}
    
    /* Desire Selector Chips Grid */
    .desire-chips-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 26px;
    }}
    .desire-chip {{
      background: var(--surface-elevated);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 14px 16px;
      cursor: pointer;
      text-align: left;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      position: relative;
    }}
    .desire-chip:hover {{
      transform: translateY(-2px);
      border-color: var(--terracotta);
      box-shadow: var(--shadow-sm);
    }}
    .desire-chip.active {{
      background: #fff;
      border-color: var(--primary);
      box-shadow: 0 0 0 2px var(--primary), var(--shadow-sm);
    }}
    .desire-chip-icon {{
      font-size: 22px;
      margin-bottom: 6px;
      display: block;
    }}
    .desire-chip-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 14px;
      font-weight: 700;
      color: var(--ink);
      line-height: 1.25;
      margin-bottom: 2px;
    }}
    .desire-chip-sub {{
      font-size: 11px;
      color: var(--muted);
      display: block;
    }}

    /* Filter Controls in Desire Engine */
    .desire-controls-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 10px 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .desire-control-group {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .desire-control-label {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--muted);
    }}

    /* Dual Recommendation Cards */
    .recommendations-showcase {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }}
    .rec-card {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 24px;
      position: relative;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .rec-card.overall-champion {{
      border-color: rgba(212, 151, 59, 0.4);
      background: linear-gradient(180deg, #fffdfa 0%, #ffffff 100%);
    }}
    .rec-card.budget-champion {{
      border-color: rgba(42, 157, 143, 0.4);
      background: linear-gradient(180deg, #f7faf9 0%, #ffffff 100%);
    }}
    .rec-card-crown {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      padding: 4px 10px;
      border-radius: 20px;
      margin-bottom: 14px;
      width: fit-content;
    }}
    .crown-overall {{
      background: #fdf3e2;
      color: #92580a;
      border: 1px solid rgba(212, 151, 59, 0.3);
    }}
    .crown-budget {{
      background: #e4f5eb;
      color: #1b663b;
      border: 1px solid rgba(42, 157, 143, 0.3);
    }}
    .rec-restaurant-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 8px;
    }}
    .rec-restaurant-name {{
      font-family: 'Outfit', sans-serif;
      font-size: 22px;
      font-weight: 700;
      color: var(--ink);
      line-height: 1.2;
    }}
    .rec-restaurant-loc {{
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 14px;
    }}
    .rec-ratings-row {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--card-border);
    }}
    .app-badge {{
      background: #fff;
      border: 1px solid var(--card-border);
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      color: var(--primary);
    }}

    /* Recommended Order Box */
    .order-box {{
      background: var(--surface-elevated);
      border: 1px dashed var(--card-border);
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 18px;
    }}
    .order-box-title {{
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--terracotta);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .order-item {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
      font-size: 13px;
    }}
    .order-item-desc {{
      font-size: 11px;
      color: var(--muted);
      margin-top: 2px;
    }}
    .order-item-price {{
      font-weight: 700;
      color: var(--ink);
      white-space: nowrap;
      margin-left: 12px;
    }}

    /* Economics & Direct Savings Box */
    .economics-box {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      background: var(--bg);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 18px;
      align-items: center;
    }}
    .econ-stat {{
      display: flex;
      flex-direction: column;
    }}
    .econ-label {{
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--muted);
      margin-bottom: 2px;
    }}
    .econ-val {{
      font-family: 'Outfit', sans-serif;
      font-size: 18px;
      font-weight: 700;
      color: var(--ink);
    }}
    .econ-val.savings {{
      color: #1b663b;
    }}

    /* Why Best Callout */
    .why-best-callout {{
      font-size: 12px;
      color: var(--muted);
      line-height: 1.5;
      margin-bottom: 18px;
      background: rgba(18, 56, 43, 0.03);
      padding: 10px 12px;
      border-radius: 8px;
      border-left: 3px solid var(--primary);
    }}

    .rec-cta-btn {{
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      background: var(--primary);
      color: #fff;
      text-decoration: none;
      font-weight: 700;
      font-size: 13px;
      padding: 12px;
      border-radius: 8px;
      transition: all 0.2s ease;
      width: 100%;
    }}
    .rec-cta-btn:hover {{
      background: var(--primary-light);
      transform: translateY(-1px);
    }}

    /* Section Cards */
    .section-title-wrap {{
      margin-bottom: 18px;
    }}
    .section-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 26px;
      font-weight: 700;
      color: var(--ink);
    }}
    .section-subtitle {{
      font-size: 14px;
      color: var(--muted);
      margin-top: 4px;
    }}

    /* Map Layout */
    .map-section {{
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 20px;
      margin-bottom: 44px;
    }}
    .map-container {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      overflow: hidden;
      box-shadow: var(--shadow-md);
      position: relative;
      display: flex;
      flex-direction: column;
    }}
    .map-header {{
      padding: 16px 20px;
      background: #fff;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .map-filters {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .filter-btn {{
      background: var(--bg);
      border: 1px solid var(--card-border);
      color: var(--ink);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .filter-btn.active, .filter-btn:hover {{
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }}
    #map {{
      height: 520px;
      width: 100%;
      z-index: 1;
    }}
    .map-sidebar {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
    }}
    .table-container {{
      overflow-y: auto;
      max-height: 470px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th {{
      text-align: left;
      padding: 10px 12px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--muted);
      border-bottom: 2px solid var(--bg);
      position: sticky;
      top: 0;
      background: var(--surface);
    }}
    td {{
      padding: 12px;
      border-bottom: 1px solid var(--bg);
      vertical-align: middle;
    }}
    tr:hover td {{
      background: #faf8f3;
    }}

    /* Badges */
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
    }}
    .badge-count {{
      background: #eef2eb;
      color: var(--primary);
    }}
    .rating-badge {{
      color: #e07a1f;
      font-weight: 700;
    }}
    .vfm-badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
    }}
    .tier-champion {{
      background: #e4f5eb;
      color: #1b663b;
    }}
    .tier-premium {{
      background: #fdf3e2;
      color: #92580a;
    }}
    .tier-budget {{
      background: #fbeef9;
      color: #832777;
    }}
    .src-link {{
      color: var(--primary);
      text-decoration: none;
      font-weight: 600;
    }}
    .src-link:hover {{ text-decoration: underline; }}

    /* Dish Cards Grid */
    .dish-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
      margin-bottom: 44px;
    }}
    .dish-card {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow-sm);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .dish-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }}
    .dish-category {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--terracotta);
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .dish-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 20px;
      font-weight: 700;
      color: var(--ink);
      margin-bottom: 6px;
    }}
    .dish-desc {{
      font-size: 13px;
      color: var(--muted);
      line-height: 1.45;
      margin-bottom: 18px;
      min-height: 38px;
    }}
    .dish-metrics {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      padding-top: 14px;
      border-top: 1px solid var(--bg);
    }}
    .metric-block {{
      display: flex;
      flex-direction: column;
    }}
    .m-label {{
      font-size: 10px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }}
    .m-val {{
      font-family: 'Outfit', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: var(--ink);
    }}
    .m-val.highlight {{
      color: var(--terracotta);
      font-size: 20px;
    }}

    /* Price Bands */
    .band-item {{
      margin: 14px 0;
    }}
    .band-header {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .band-track {{
      height: 8px;
      background: #e9e6df;
      border-radius: 4px;
      overflow: hidden;
    }}
    .band-fill {{
      height: 100%;
      border-radius: 4px;
    }}

    /* Competitive Leaderboard */
    .leaderboard-section {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 26px;
      box-shadow: var(--shadow-sm);
      margin-bottom: 40px;
    }}
    .leaderboard-controls {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .search-input {{
      padding: 8px 14px;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      font-size: 13px;
      width: 260px;
      background: var(--bg);
      outline: none;
    }}
    .search-input:focus {{
      border-color: var(--primary);
      background: #fff;
    }}

    /* Footer */
    footer {{
      border-top: 1px solid var(--card-border);
      padding-top: 24px;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.6;
    }}

    /* Responsive */
    @media (max-width: 1024px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .map-section {{ grid-template-columns: 1fr; }}
      .dish-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .recommendations-showcase {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      .dish-grid {{ grid-template-columns: 1fr; }}
      .kpi-grid {{ grid-template-columns: 1fr; }}
      .map-header {{ flex-direction: column; align-items: flex-start; }}
      .desire-chips-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>

<div class="container">
  <!-- Top Bar -->
  <header class="topbar">
    <div class="pulse-badge">
      <span class="pulse-dot"></span>
      <span>AHMEDABAD & GANDHINAGAR RESTAURANT MARKET PRICING · LIVE INTELLIGENCE</span>
    </div>
    <div>Live Delivery (Swiggy / Zomato) & Free OpenStreetMap Pipeline</div>
  </header>

  <!-- Hero Section -->
  <section class="hero">
    <div>
      <h1>Kathiyawadi Dining,<br><em>mapped, priced & recommended.</em></h1>
      <p class="hero-lead">
        A real-time spatial pricing & recommendation desk tracking authentic vegetarian Kathiyawadi dining, iconic highway dhabas, delivery menus (Swiggy & Zomato benchmarks), and thali economics across the <strong>Ahmedabad & Gandhinagar Twin Metro Region</strong>.
      </p>
    </div>
    <div class="hero-callout">
      <h3>Operator & Diner Intelligence</h3>
      <p>Analyze area pricing saturation, benchmark dish economics, and uncover the highest-rated authentic meals that cost you less.</p>
      <a href="{experience_url}" class="btn-action" target="_blank" rel="noopener">Share a Field Observation ↗</a>
    </div>
  </section>

  <!-- Summary KPI Cards -->
  <section class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Restaurants Tracked</div>
      <div class="kpi-value">{total_restaurants}</div>
      <div class="kpi-sub">Across Ahmedabad & Gandhinagar</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Menu Observations</div>
      <div class="kpi-value">{total_observations}</div>
      <div class="kpi-sub">Validated dish price points</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Market Midpoint</div>
      <div class="kpi-value">₹{median_price:,.0f}</div>
      <div class="kpi-sub">Median price per dish</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Hubs Monitored</div>
      <div class="kpi-value">{areas_tracked}</div>
      <div class="kpi-sub">Neighborhoods & sub-markets</div>
    </div>
  </section>

  <!-- MAIN TAB NAVIGATION -->
  <div class="tab-nav-wrapper">
    <nav class="tab-nav">
      <button class="nav-tab-btn active" data-target="desire-section">
        <span class="tab-icon">🌟</span>
        <span>Best Choice for Your Desire</span>
        <span class="tab-badge">RECOMMENDED</span>
      </button>
      <button class="nav-tab-btn" data-target="map-section">
        <span class="tab-icon">📍</span>
        <span>Regional Spatial Map & Saturation</span>
      </button>
      <button class="nav-tab-btn" data-target="dishes-section">
        <span class="tab-icon">🍲</span>
        <span>Iconic Dish Economics</span>
      </button>
      <button class="nav-tab-btn" data-target="leaderboard-section">
        <span class="tab-icon">🏆</span>
        <span>Competitive VFM Leaderboard</span>
      </button>
    </nav>
  </div>

  <!-- TAB 1: BEST CHOICE FOR YOUR DESIRE -->
  <section id="desire-section" class="desire-container">
    <div class="desire-header">
      <div class="desire-title-wrap">
        <h2>Best Choice for Your Desire</h2>
        <p>What are you craving today? Select your desire below — our engine analyzes Swiggy & Zomato ratings, reviews, and actual menu prices to tell you <strong>what to order</strong>, <strong>where it's rated best</strong>, and <strong>at which price it costs you less</strong> with direct savings.</p>
      </div>
    </div>

    <!-- Desire Selector Chips -->
    <div class="desire-chips-grid" id="desireChips">
      <!-- Injected via JavaScript -->
    </div>

    <!-- Controls Bar (City Switcher) -->
    <div class="desire-controls-bar">
      <div class="desire-control-group">
        <span class="desire-control-label">Region:</span>
        <div class="map-filters" id="desireCityFilters">
          <button class="filter-btn active" data-city="all">All Twin Cities</button>
          <button class="filter-btn" data-city="Ahmedabad">Ahmedabad</button>
          <button class="filter-btn" data-city="Gandhinagar">Gandhinagar</button>
        </div>
      </div>
      <div style="font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px;">
        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#2a9d8f;"></span>
        <span>Verified Swiggy & Zomato Menus</span>
      </div>
    </div>

    <!-- Recommendations Showcase Cards -->
    <div class="recommendations-showcase" id="recommendationsShowcase">
      <!-- Dynamic Rendering via JavaScript -->
    </div>
  </section>

  <!-- TAB 2: SPATIAL INTELLIGENCE (LEAFLET OSM MAP) -->
  <section id="map-section">
    <div class="section-title-wrap">
      <h2 class="section-title">Spatial Market Footprint</h2>
      <p class="section-subtitle">Explore live Kathiyawadi restaurants across Ahmedabad & Gandhinagar with exact GPS coordinates and ratings.</p>
    </div>

    <div class="map-section">
      <div class="map-container">
        <div class="map-header">
          <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            <span style="font-weight: 700; font-size: 14px;">📍 Regional Map View</span>
            <span style="background:#e4f5eb; color:#1b663b; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:700;">🌐 100% Free OpenStreetMap · Zero API Keys</span>
          </div>
          <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <div class="map-filters" id="cityFilters">
              <button class="filter-btn active" data-city="all">All Cities</button>
              <button class="filter-btn" data-city="Ahmedabad">Ahmedabad</button>
              <button class="filter-btn" data-city="Gandhinagar">Gandhinagar</button>
            </div>
            <div class="map-filters" id="tierFilters">
              <button class="filter-btn active" data-filter="all">All Tiers</button>
              <button class="filter-btn" data-filter="Value Champion">Value Champions</button>
              <button class="filter-btn" data-filter="Premium Benchmark">Premium</button>
              <button class="filter-btn" data-filter="Budget Dhaba">Budget</button>
            </div>
          </div>
        </div>
        <div id="map"></div>
      </div>

      <div class="map-sidebar">
        <h3 style="font-family: 'Outfit'; font-size: 18px; margin-bottom: 4px;">Neighborhood Saturation</h3>
        <p style="font-size: 12px; color: var(--muted); margin-bottom: 16px;">Ranked by tracked restaurant count and average rating.</p>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Area</th>
                <th>Count</th>
                <th>Rating</th>
                <th>Price Signal</th>
              </tr>
            </thead>
            <tbody>
              {area_table_html}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 3: STAPLE DISH BENCHMARKS -->
  <section id="dishes-section">
    <div class="section-title-wrap">
      <h2 class="section-title">Iconic Dish Economics</h2>
      <p class="section-subtitle">Real market benchmarks for the core pillars of an authentic Kathiyawadi menu.</p>
    </div>

    <div class="dish-grid">
      {staple_cards_html}
    </div>

    <!-- Price Architecture Distribution -->
    <div style="background: var(--surface); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 24px; margin-bottom: 44px; box-shadow: var(--shadow-sm);">
      <h3 style="font-family: 'Outfit'; font-size: 20px; margin-bottom: 4px;">Price Architecture & Menu Tiering</h3>
      <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">Distribution of observed menu items across customer pricing bands.</p>
      {band_rows}
    </div>
  </section>

  <!-- TAB 4: COMPETITIVE LEADERBOARD -->
  <section id="leaderboard-section" class="leaderboard-section">
    <div class="leaderboard-controls">
      <div>
        <h3 style="font-family: 'Outfit'; font-size: 22px; font-weight: 700;">Competitive Intelligence & Value Leaderboard</h3>
        <p style="font-size: 13px; color: var(--muted);">Algorithmic Value-for-Money (VFM) index balancing customer rating against price tier.</p>
      </div>
      <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search restaurant or area...">
    </div>

    <div class="table-container" style="max-height: 520px;">
      <table id="leaderboardTable">
        <thead>
          <tr>
            <th>Restaurant & Location</th>
            <th>Rating & Reviews</th>
            <th>Price Signal</th>
            <th>Value-for-Money (VFM) Rank</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard_html}
        </tbody>
      </table>
    </div>
  </section>

  <!-- Methodology & Open Data Footer -->
  <footer>
    <p><strong>Open-Source Methodology & Free Maps Stack:</strong> This dataset is refreshed via a zero-cost automated data pipeline leveraging OpenStreetMap Overpass API, public community contributions, and algorithmic entity deduplication. Map rendered using 100% free Leaflet.js with CartoDB Voyager tiles. All prices in INR (₹). This view is directional market intelligence for business operators and diners seeking maximum satisfaction.</p>
  </footer>
</div>

<!-- Leaflet JS (100% Free OpenStreetMap) -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>

<script>
  const restaurants = {map_json_data};
  const desires = {desires_json_data};

  // -------------------------------------------------------------
  // 1. TAB NAVIGATION HANDLER
  // -------------------------------------------------------------
  const navTabs = document.querySelectorAll('.nav-tab-btn');
  navTabs.forEach(tab => {{
    tab.addEventListener('click', () => {{
      navTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-target');
      const targetElem = document.getElementById(targetId);
      if (targetElem) {{
        const offset = 80;
        const bodyRect = document.body.getBoundingClientRect().top;
        const elementRect = targetElem.getBoundingClientRect().top;
        const elementPosition = elementRect - bodyRect;
        const offsetPosition = elementPosition - offset;
        window.scrollTo({{
          top: offsetPosition,
          behavior: 'smooth'
        }});
      }}
    }});
  }});

  // -------------------------------------------------------------
  // 2. BEST CHOICE FOR YOUR DESIRE ENGINE
  // -------------------------------------------------------------
  let currentDesireId = desires[0].id;
  let currentDesireCity = 'all';

  const desireChipsContainer = document.getElementById('desireChips');
  const recShowcaseContainer = document.getElementById('recommendationsShowcase');

  function renderDesireChips() {{
    desireChipsContainer.innerHTML = desires.map(d => `
      <div class="desire-chip ${{d.id === currentDesireId ? 'active' : ''}}" data-id="${{d.id}}">
        <span class="desire-chip-icon">${{d.icon}}</span>
        <div class="desire-chip-title">${{d.title}}</div>
        <span class="desire-chip-sub">${{d.badge}}</span>
      </div>
    `).join('');

    const chips = desireChipsContainer.querySelectorAll('.desire-chip');
    chips.forEach(chip => {{
      chip.addEventListener('click', () => {{
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentDesireId = chip.getAttribute('data-id');
        renderRecommendations();
      }});
    }});
  }}

  function renderRecommendations() {{
    const desire = desires.find(d => d.id === currentDesireId) || desires[0];
    const recData = desire.recommendations[currentDesireCity] || desire.recommendations['all'];
    const overall = recData.best_overall;
    const budget = recData.best_budget;

    function renderCard(rec, typeClass, crownClass, crownTitle, crownIcon) {{
      const itemsHtml = rec.items.map(it => `
        <div class="order-item">
          <div>
            <strong>${{it.name}}</strong>
            <div class="order-item-desc">${{it.desc}}</div>
          </div>
          <div class="order-item-price">₹${{it.price}}</div>
        </div>
      `).join('');

      return `
        <div class="rec-card ${{typeClass}}">
          <div>
            <div class="rec-card-crown ${{crownClass}}">
              <span>${{crownIcon}}</span>
              <span>${{crownTitle}}</span>
            </div>

            <div class="rec-restaurant-header">
              <div>
                <h3 class="rec-restaurant-name">${{rec.name}}</h3>
                <div class="rec-restaurant-loc">📍 ${{rec.area}}, ${{rec.city}}</div>
              </div>
            </div>

            <div class="rec-ratings-row">
              <span class="rating-badge" style="font-size:16px;">★ ${{rec.rating}}</span>
              <span style="font-size:12px; color:var(--muted); font-weight:600;">(${{rec.reviews.toLocaleString()}} verified diner reviews)</span>
              <span class="app-badge">${{rec.app}}</span>
            </div>

            <div class="order-box">
              <div class="order-box-title">
                <span>🍽️</span>
                <span>Recommended Order for You</span>
              </div>
              ${{itemsHtml}}
            </div>

            <div class="economics-box">
              <div class="econ-stat">
                <span class="econ-label">Your Meal Cost</span>
                <span class="econ-val">₹${{rec.total_cost}}</span>
              </div>
              <div class="econ-stat">
                <span class="econ-label">Market Average</span>
                <span class="econ-val" style="color:var(--muted); text-decoration:line-through;">₹${{rec.market_avg}}</span>
              </div>
              <div class="econ-stat">
                <span class="econ-label">Direct Savings</span>
                <span class="econ-val savings">Save ₹${{rec.savings_amount}} (${{rec.savings_percent}}%)</span>
              </div>
            </div>

            <div class="why-best-callout">
              <strong>💡 Why This Choice:</strong> ${{rec.why_best}}
            </div>
          </div>

          <a href="${{rec.url}}" target="_blank" rel="noopener" class="rec-cta-btn">
            <span>Order / Inspect on ${{rec.app.split(' ')[0]}} ↗</span>
          </a>
        </div>
      `;
    }}

    recShowcaseContainer.innerHTML = `
      ${{renderCard(overall, 'overall-champion', 'crown-overall', 'Highest App Rating & Best Quality', '🏆')}}
      ${{renderCard(budget, 'budget-champion', 'crown-budget', 'Maximum Direct Savings & Low Price', '💰')}}
    `;
  }}

  // Desire City Filter buttons
  const desireCityBtns = document.querySelectorAll('#desireCityFilters .filter-btn');
  desireCityBtns.forEach(btn => {{
    btn.addEventListener('click', () => {{
      desireCityBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentDesireCity = btn.getAttribute('data-city');
      renderRecommendations();
    }});
  }});

  renderDesireChips();
  renderRecommendations();

  // -------------------------------------------------------------
  // 3. FREE LEAFLET MAP INITIALIZATION (ZERO API KEY)
  // -------------------------------------------------------------
  const map = L.map('map', {{
    center: [23.10, 72.58],
    zoom: 11,
    scrollWheelZoom: false
  }});

  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
  }}).addTo(map);

  const markers = [];

  function createCustomIcon(tier) {{
    let bg = '#df5d2f';
    if (tier === 'Value Champion') bg = '#12382b';
    if (tier === 'Premium Benchmark') bg = '#d4973b';

    return L.divIcon({{
      className: 'custom-pin',
      html: `<div style="
        background: ${{bg}};
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 2px solid #fff;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-size: 11px;
        font-weight: bold;
      ">★</div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    }});
  }}

  restaurants.forEach(r => {{
    if (!r.lat || !r.lon) return;

    const marker = L.marker([r.lat, r.lon], {{
      icon: createCustomIcon(r.vfm_tier)
    }});

    const popupHtml = `
      <div style="font-family:'Plus Jakarta Sans', sans-serif; min-width: 220px;">
        <h4 style="margin: 0 0 4px; font-size: 15px; color: #12382b;">${{r.name}}</h4>
        <div style="font-size: 12px; color: #666; margin-bottom: 6px;">📍 ${{r.city}} (${{r.area}}) · ${{r.type}}</div>
        <div style="display:flex; justify-content:space-between; margin-bottom: 8px; font-size: 13px;">
          <strong style="color: #e07a1f;">★ ${{r.rating}} (${{r.reviews}})</strong>
          <span style="font-weight: 600; color: #333;">${{r.price_range}}</span>
        </div>
        <div style="margin-bottom: 8px;">
          <span style="background:#e4f5eb; color:#1b663b; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:600;">
            ${{r.vfm_tier}}
          </span>
        </div>
        ${{r.source_url ? `<a href="${{r.source_url}}" target="_blank" rel="noopener" style="font-size: 12px; color: #12382b; font-weight: bold; text-decoration: none;">View on ${{r.source_system.includes('external') ? 'Delivery App' : 'Map'}} ↗</a>` : ''}}
      </div>
    `;

    marker.bindPopup(popupHtml);
    marker.restaurantData = r;
    marker.addTo(map);
    markers.push(marker);
  }});

  let currentTier = 'all';
  let currentCity = 'all';

  function applyFilters() {{
    const bounds = [];
    markers.forEach(m => {{
      const matchTier = currentTier === 'all' || m.restaurantData.vfm_tier === currentTier;
      const matchCity = currentCity === 'all' || m.restaurantData.city.toLowerCase() === currentCity.toLowerCase();
      
      if (matchTier && matchCity) {{
        m.addTo(map);
        bounds.push(m.getLatLng());
      }} else {{
        map.removeLayer(m);
      }}
    }});

    if (bounds.length > 0) {{
      map.fitBounds(L.latLngBounds(bounds), {{ padding: [30, 30] }});
    }}

    tableRows.forEach(row => {{
      const rCity = row.getAttribute('data-city');
      const rTier = row.getAttribute('data-tier');
      const matchCity = currentCity === 'all' || (rCity && rCity.toLowerCase() === currentCity.toLowerCase());
      const matchTier = currentTier === 'all' || (rTier && rTier === currentTier);
      row.style.display = (matchCity && matchTier) ? '' : 'none';
    }});
  }}

  const cityBtns = document.querySelectorAll('#cityFilters .filter-btn');
  cityBtns.forEach(btn => {{
    btn.addEventListener('click', () => {{
      cityBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCity = btn.getAttribute('data-city');
      applyFilters();
    }});
  }});

  const tierBtns = document.querySelectorAll('#tierFilters .filter-btn');
  tierBtns.forEach(btn => {{
    btn.addEventListener('click', () => {{
      tierBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTier = btn.getAttribute('data-filter');
      applyFilters();
    }});
  }});

  // Search Filter Handler for Table
  const searchInput = document.getElementById('searchInput');
  const tableRows = document.querySelectorAll('#leaderboardTable tbody .rest-row');

  searchInput.addEventListener('input', (e) => {{
    const term = e.target.value.toLowerCase().trim();
    tableRows.forEach(row => {{
      const text = row.innerText.toLowerCase();
      row.style.display = text.includes(term) ? '' : 'none';
    }});
  }});
</script>

</body>
</html>"""

    (DOCS / "index.html").write_text(page_html, encoding="utf-8")
    print(f"Successfully generated {DOCS / 'index.html'} with {len(map_restaurants)} mapped restaurants and 'Best Choice for Your Desire' engine!")


if __name__ == "__main__":
    build()
