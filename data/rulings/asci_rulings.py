# Hand-extracted from ASCI Consumer Complaints Council press releases (read 28 Oct 2026). Each entry's
# claims are quoted from the release; every one of these complaints was UPHELD (the releases list upheld
# complaints). `verify.py` checks every quote against the PDF text.
U = "upheld"
BASE = "https://www.ascionline.in/wp-content/uploads/2022/09/"
A = dict(url=BASE + "asci_oct_nov18_ccc_recom.pdf", date="2019-03-01", period="Oct-Nov 2018")
B = dict(url=BASE + "asci_sept18_ccc_recom.pdf", date="2018-12-18", period="Aug-Sep 2018")
C = dict(url=BASE + "asci-oct-ccc.pdf", date="2017-12-28", period="Oct 2017")


def e(n, doc, advertiser, product, medium, claims, issue="substantiation"):
    return dict(id=f"ASCI-{n:03d}", source="ASCI", date=doc["date"], period=doc["period"], advertiser=advertiser,
                product=product, medium=medium, url=doc["url"], ad_text="\n".join(claims),
                claims=[dict(text=c, outcome=U, why="Complaint upheld: not substantiated or misleading.", issue=issue) for c in claims])


ASCI = [
 e(1, A, "Procter & Gamble Hygiene & Health Care", "Head & Shoulders anti-dandruff shampoo", "print/digital", ["Keeps you up to 100% dandruff free"], "misleading-implication"),
 e(2, A, "Procter & Gamble Hygiene & Health Care", "Head & Shoulders anti-dandruff shampoo", "print", ["Dandruff free smooth baal, Rs 2 ka kamaal"], "misleading-implication"),
 e(3, A, "GlaxoSmithKline Asia", "Sensodyne toothpaste", "advertisement", ["That's Why Dentist Recommended", "Eight out of 10 dentists recommend Sensodyne for sensitive teeth"]),
 e(4, A, "Ratan Ayurvedic Sansthan", "Sugandha Varna Nikhar cream", "advertisement", ["It reduces melanin formation and makes your skin fairer day by day"]),
 e(5, A, "Himalaya Drug Company", "Himalaya Anti Hair Fall shampoo", "advertisement", ["Hair Fall ka Sahi Solution"]),
 e(6, A, "Mountain Valley Springs India", "Forest Essentials Sanjeevani Beauty Elixir", "advertisement", ["The formulation is an enriched version of natural sebum, which instantly penetrates and plumps the skin", "This potent formula has powerful anti-ageing properties that visibly diminishes signs of ageing by eliminating fine lines and restoring firmness, leaving the skin firm, toned and more youthful"]),
 e(7, A, "Mountain Valley Springs India", "Forest Essentials Eternal Youth Formula", "advertisement", ["most effective and precious ingredients"]),
 e(8, A, "Mountain Valley Springs India", "Forest Essentials Kumkumadi Teenage Night Cream", "advertisement", ["Kumkumadikeram night cream is a highly effective night cream which contains powerful Ayurvedic preparations of Kumkumadikeram and Manikya (Ruby) Bhasma which helps to lighten pigmentation and clarify the skin", "ManikyaBhasma has miraculous skin rejuvenating properties"]),
 e(9, A, "Shree Sanjeevan Wellness Solutions", "Pure Elements Age Defying cream", "advertisement", ["It regenerates cellular tissue and collagen and slows down skin ageing", "Prevents wrinkle formation, removes dark patches and restores skin elasticity and firmness", "Precious ingredients of this cream fight free radicles and prevent oxidative damage caused by UV rays and pollution"]),
 e(10, A, "Shree Sanjeevan Wellness Solutions", "Pure Elements ultra light sunscreen", "advertisement", ["Enriched with botanical extracts and vitamins, this formulation offers powerful protection against free radicals", "Infused with natural extracts of herbs & roots, it gives perfect protection against ageing, dark spots, blemishes and skin darkening"]),
 e(11, A, "Namyaa Skincare", "Namyaa Intimate Lightening Serum", "advertisement", ["This great formula not only lightens the dark pigmentation but also removes cellulite and scars of the skin to make it radiant and glowing", "Get a flawless and graceful skin of intimate areas by Namyaa Intimate Skin Whitening gel in just six to eight weeks"]),
 e(12, A, "Eli Pharmaceuticals", "Melas cream and lotion", "advertisement", ["Glow and shine on face", "Effective from day one itself"]),
 e(13, C, "Reckitt Benckiser (India)", "Veet wax strips", "advertisement", ["Removes the shortest hair that salon wax cannot"]),
 e(14, C, "Hamdard Laboratories (India)", "Safi", "advertisement", ["For pimple free skin 21 days formula", "For pimple free skin"], "substantiation"),
 e(15, C, "Brihans Natural Products", "Green Leaf pure aloe vera skin gel", "advertisement", ["India's most trusted brand", "Unlike any cream and oil based cosmetic products, this Ayurvedic Aloe Gel naturally protects your skin"]),
 e(16, C, "Himalaya Drug Company", "Himalaya Purifying Neem Face Wash", "advertisement", ["gives you pimple-free pure skin", "Prevents pimples"]),
 e(17, C, "CavinKare", "Egg White Chik shampoo", "advertisement", ["Eh damaged baloonko nourish karkehairfallkamkare"]),
 e(18, C, "Pfizer", "Anne French All Natural hair removal cream", "advertisement", ["Anne French All Natural Apnao", "2x softer skin"], "misleading-implication"),
 e(19, B, "Hindustan Unilever", "Lever Ayush Antimarks Turmeric face cream", "advertisement", ["A skin care treatment formulated with 5000 years of Ayurvedic wisdom from the granthas", "The purifying properties of Turmeric (haldi) are known to enhance complexion", "Kumkumadi Tailam is known to cure marks"]),
 e(20, B, "Hindustan Unilever", "Lever Ayush Natural Fairness Saffron face cream", "advertisement", ["A fairness treatment formulated with 5000 years of Ayurvedic wisdom", "The rich blend of Saffron and Kumkumadi Tailam is known to cure marks and lighten skin complexion"]),
 e(21, B, "Hindustan Unilever", "Pure Derm shampoo", "advertisement", ["100% tak Dandruff Jayega Aur Waapas Nahin Aayega"], "misleading-implication"),
 e(22, B, "Hindustan Unilever", "Indulekha Bringha Oil", "TV commercial", ["grows new hair"]),
 e(23, B, "Wipro Enterprises", "Chandrika hair oil", "advertisement", ["arrests hair fall and makes your hair thicker and stronger"]),
 e(24, B, "OJB Herbals", "Oshea Herbals UV Shield sunscreen gel", "advertisement", ["Protects you from all forms of sun damage like tanning, sun spots and premature ageing", "Lightens skin by regulating skin darkening pigments"]),
 e(25, B, "Apcos Naturals", "Just Herbs Fair'e and A'ffair", "advertisement", ["Our Fair'e skin lightening gel and A'ffair skin lightening cream help in getting rid of dark spots and patches", "The herbs present in them detoxify the blood and boost circulation to fade freckles and skin discolorations thus making the skin tone more even toned and giving it a lighter appearance"]),
 e(26, B, "Vaadi Herbals", "Vaadi 24 Carat Gold face pack", "advertisement", ["This rich gold pack is specially formulated with high percentage of 24 carat gold leaves which gives an instant shine and lustre to the facial skin"]),
]
