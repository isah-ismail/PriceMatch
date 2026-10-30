# -*- coding: utf-8 -*-
"""
Happy Center (happycenter.com.tr) - Gıda ve alkolsüz içecek fiyat scraper'ı (HTML, tarayıcısız)

Konum:       Bu dosya repoda InflationItems/Codes/01_Food/HappyCenter/ klasöründe durmalı.

Çıktı:
  InflationItems/Datas/01_Food/HappyCenter/happycenter_YYYY-MM-DD.csv
  -> product_name, price, category_number, sub_category_number
  (Grup 01'in ortak formatı, bkz. Codes/01_Food/coicop_food/README.md)

Çalışma mantığı:
  Ana sayfa menüsünden Kuru Gıda ve Taze Ürünler altındaki gruplar alınır. Her grup
  sayfasındaki "Reyon Seçiniz" listesiyle en alt reyona inilir ve reyon ?page=N ile
  sayfa sayfa okunur. Fiyat, ürün kartındaki fiyattır (misafir kullanıcıya gösterilen).

Copied from the inflation study (InflationResearchStudy, commit 70d13e445,
InflationItems/Codes/01_Food/HappyCenter/happycenter_scraper.py) for
happycenter_specs.py. Changes: the daily CSV paths, main() and the pandas import are
removed (this copy only fetches), and parse_products() also reads each image.
"""
import datetime
import html
import re
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

import requests

BASE = "https://www.happycenter.com.tr"
TODAY = datetime.datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()

SLEEP = 0.5

# Grup 01'in ortak CSV başlıkları (coicop_food.FIELDS ile aynı). Kodları kendi
# kurallarımız verdiği için ortak modülü içe aktarmıyoruz: 0 verdiğimiz ürünler
# bilinçli olarak 0 (sepette karşılığı yok); ortak kurallar bunları çoğunlukla
# yanlış koda taşıyordu (ör. salamura asma yaprağı -> dana salam).
FIELDS = ["product_name", "price", "category_number", "sub_category_number"]
MAX_PAGES = 150          # sadece güvenlik sınırı (en büyük reyon ~80 sayfa)
MAX_DEPTH = 4
# True: üst reyonun sitedeki ürün sayısı, alt reyonlardan gelen ürün sayısıyla birebir
# aynı değilse üst reyonun sayfaları da taranır (bazı ürünler hiçbir alt reyonda yok).
CHECK_PARENT_PRODUCTS = True

# Menüde bu yollarla başlayan gruplar taranır (Gıda Dışı hariç)
FOOD_ROOTS = ["Kuru_Gıda", "Taze_Ürünler"]

# Bu kelimeleri içeren reyonlar dışarıda kalır
EXCLUDE = ["alkol", "bira", "sarap", "raki", "viski", "votka", "sigara", "tutun",
           "temizlik", "deterjan", "kozmetik", "bakim", "bezi", "bezleri", "mendil",
           "kedi", "kopek", "evcil", "oyuncak", "kirtasiye"]

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
session = requests.Session()
session.headers.update(HEADERS)


# ---------- yardımcılar ----------
def norm(s):
    s = (s or "").replace("I", "ı").replace("İ", "i").lower()
    for a, b in zip("çğıöşüâî", "cgiosuai"):
        s = s.replace(a, b)
    return " ".join(re.split(r"[^a-z0-9]+", s)).strip()


def has_kw(text, kws):
    padded = f" {norm(text)} "
    words = padded.split()
    for kw in kws:
        if " " in kw:
            if f" {kw} " in padded:
                return True
        elif any((w.startswith(kw) if len(kw) >= 4 else w == kw) for w in words):
            return True
    return False


def clean(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def to_float(s):
    """'1.234,56' -> 1234.56 (sitede Türkçe biçim: nokta binlik, virgül ondalık)."""
    try:
        return float(s.replace(".", "").replace(",", "."))
    except (AttributeError, ValueError):
        return None


def seg_name(url):
    """'/Taze_Ürünler/Sütlük_Grubu' -> 'Sütlük Grubu'"""
    last = unquote(urlparse(url).path).rstrip("/").split("/")[-1]
    return last.replace("_", " ").strip()


def get_html(url, params=None):
    for attempt in range(3):
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.content.decode("utf-8", errors="replace")
            print(f"    ! HTTP {r.status_code}: {r.url}")
            if r.status_code == 404:
                return None
        except Exception as e:
            print(f"    ! Hata ({attempt + 1}/3): {e}")
        time.sleep(2)
    return None


# ---------- TÜİK alt kategori eşleştirmesi ----------
# Her site reyonu için kurallar sırayla denenir, ilk eşleşen kod yazılır.
# "a+b" = ürün adında hem a hem b geçmeli. "*" = reyon içindeki varsayılan kod.
# Hiçbir kurala uymayan ya da TÜİK listesinde karşılığı olmayan ürünler 0 alır.
# Önceki marketlerle tutarlı kararlar: kek/kruvasan 0111392, enerji içeceği ve limonata
# 0126002, kola 0126003, toz puding 0119904, hazır puding 0114701, sadece bebek/devam
# sütü 0119212; kefir, şalgam, noodle, bulyon, karışık kuruyemiş, kaju, donuk sebze 0.
# Ortak listeler (_PEYNIR, _SUT ...) birden çok site reyonunda kullanılır.
# ---- ortak kural setleri (birden çok reyonda kullanılır) ----
_SARKUTERI = [("sucuk", "0112311"), ("sucug", "0112311"), ("sosis", "0112511"), ("pilic+salam", "0112392"),
              ("hindi+salam", "0112392"), ("salam", "0112312"), ("kavurma", "0112593"),
              ("*", "0")]
_PEYNIR = [("zeytin", "0117476"), ("karper", "0114504"), ("la vache", "0114504"),
           ("eritme", "0114504"), ("light peynir", "0114501"), ("b peynir", "0114501"),
           ("mihlama", "0114505"), ("misket", "0114505"), ("surku", "0114505"), ("krem", "0114504"), ("labne", "0114504"),
           ("ucgen", "0114504"), ("surulebilir", "0114504"), ("tulum", "0114503"),
           ("eski kasar", "0114502"), ("kasar", "0114502"), ("tost", "0114502"),
           ("kaskaval", "0114502"), ("cecil", "0114505"), ("orgu", "0114505"),
           ("tel", "0114505"), ("burgu", "0114505"), ("dil peynir", "0114505"),
           ("topi", "0114505"),
           ("lor", "0114505"), ("tava", "0114505"), ("anadolu", "0114505"),
           ("hellim", "0114505"), ("otlu", "0114505"), ("sepet", "0114505"),
           ("cerkez", "0114505"), ("mihalic", "0114505"), ("kolot", "0114505"),
           ("civil", "0114505"), ("abaza", "0114505"),
           ("taze peynir", "0114505"),
           ("beyaz", "0114501"), ("ezine", "0114501"), ("salamura", "0114501"),
           ("surbeni", "0114501"), ("suzme", "0114501"), ("olgunlastirilmis", "0114501"),
           ("lokum", "0114501"), ("*", "0")]
_SUT = [("alpro", "0"), ("nilky", "0"), ("icece", "0"), ("bitkisel", "0"),
        ("ice break", "0"), ("latte", "0"), ("puding", "0114701"), ("kahve", "0114703"),
        ("milk shake", "0114703"), ("devam", "0"), ("keci", "0114111"), ("cilek", "0114703"), ("kakao", "0114703"),
        ("muzlu", "0114703"), ("cikolata", "0114703"), ("icimino", "0114703"),
        ("kido", "0114703"), ("aroma", "0114703"), ("vanilya", "0114703"),
        ("karamel", "0114703"), ("bal", "0114703"), ("yarim yagli", "0114201"),
        ("light", "0114201"), ("1 5 yagli", "0114201"), ("0 5 yagli", "0114201"),
        ("2 5 yagli", "0114201"), ("*", "0114111")]
_MAKARNA = [("noodle", "0"), ("indo mie", "0"), ("wasa", "0111394"), ("makarna sos", "0"),
            ("karabugday dane", "0"), ("ramen", "0"), ("sehriye", "0111502"),
            ("manti makarna", "0111501"), ("manti", "0119195"), ("*", "0111501")]
_ICECEK = [("kefir", "0"), ("ayran", "0114605"), ("salgam", "0"),
           ("soguk cay", "0123034"), ("ice tea", "0123034"), ("icetea", "0123034"),
           ("fuse", "0123034"), ("sogukcay", "0123034"), ("tea", "0123034"),
           ("bubble", "0"), ("serbet", "0"), ("malt", "0126002"), ("boza", "0"), ("limonata", "0126002"),
           ("multi vitamin", "0126002"), ("*", "0121001")]
_CIKOLATA = [("protein", "0"), ("tahil bar", "0"), ("yulaf", "0"), ("corny", "0"),
             ("nesfit", "0"), ("mixmey", "0"), ("delly", "0"), ("tadimca", "0"),
             ("meyve bar", "0"), ("koz helva", "0"), ("krem cikolata", "0118593"),
             ("findik kremasi", "0118593"), ("cokokrem", "0118593"),
             ("sut burger", "0111392"), ("kek", "0111392"), ("pingui", "0111392"),
             ("bisk", "0111393"), ("kraker", "0111394"), ("gofret", "0111396"),
             ("gofrik", "0111396"), ("gofibon", "0111396"), ("wafer", "0111396"),
             ("kitkat", "0111396"), ("kit kat", "0111396"), ("dido", "0111396"),
             ("cokonat", "0111396"), ("toffe", "0118995"), ("gummy", "0118995"),
             ("*", "0118512")]
_BISKUVI = [("protein", "0"), ("ozmo burger", "0111392"), ("patlag", "0"),
            ("yumurta", "0118512"), ("gofret", "0111396"), ("kraker", "0111394"),
            ("crax", "0111394"), ("cizi", "0111394"), ("grissini", "0111394"),
            ("galeta", "0111394"), ("kek", "0111392"), ("dankek", "0111392"),
            ("popkek", "0111392"), ("topkek", "0111392"), ("paykek", "0111392"),
            ("kruvasan", "0111392"), ("kuruvasan", "0111392"), ("browni", "0111392"),
            ("donut", "0111392"), ("magma", "0111392"), ("luppo", "0111392"),
            ("sut dilimi", "0111392"), ("rulo pasta", "0111392"),
            ("kat kat tat", "0111392"), ("*", "0111393")]
_SEBZE_MEYVE = [("canbas", "0"), ("dogranmis mantar", "0117452"), ("portakal suyu", "0"), ("potakal suyu", "0"), ("salamura", "0"),
                ("kavanoz", "0"), ("kavaniz", "0"), ("ezmesi", "0"), ("sirkeli", "0"),
                ("kiyilmis", "0"), ("haslanmis", "0"), ("dogranmis", "0"),
                ("dilimlenmis", "0"), ("akdeniz salata", "0"), ("yer elmasi", "0"),
                ("dolma kirmizi", "0117215"), ("dolma sari", "0117215"),
                ("mantar", "0117452"), ("sogan taze", "0"),
                ("brokoli", "0"), ("bruksel", "0"), ("kara demet", "0"),
                ("lahana", "0117123"), ("carliston", "0117211"),
                ("biberiye", "0119401"), ("biber", "0117215"), ("dereotu", "0119401"),
                ("maydanoz", "0119401"), ("maydonoz", "0119401"), ("nane", "0119401"),
                ("roka", "0119401"), ("tere", "0119401"), ("reyhan", "0119401"),
                ("feslegen", "0119401"), ("kekik", "0119401"),
                ("domates", "0117241"), ("fasulye", "0117312"), ("fasulye", "0117312"),
                ("gobek", "0117141"), ("kivircik", "0117141"), ("marul", "0117141"),
                ("ispanak", "0117151"), ("havuc", "0117410"), ("balkabag", "0"),
                ("kabak", "0117253"), ("karnabahar", "0117131"), ("karnibahar", "0117131"),
                ("lime", "0"), ("limon", "0116221"), ("taze sogan", "0"),
                ("yesil sogan", "0"), ("sogan", "0117431"), ("tatli patates", "0"),
                ("patates", "0117511"), ("patlican", "0117234"), ("mantar", "0117452"),
                ("salatalik", "0117222"), ("pirasa", "0117445"), ("turp", "0117416"),
                ("sarimsak", "0117421"),
                ("elma", "0116311"), ("muz", "0116121"), ("mandalina", "0116241"),
                ("portakal", "0116231"), ("nar", "0116591"), ("armut", "0116321"),
                ("ayva", "0116321"), ("uzum", "0116511"), ("seftali", "0116351"),
                ("cilek", "0116451"), ("kivi", "0116521"), ("kavun", "0116531"),
                ("karpuz", "0116541"), ("*", "0")]
_MEZE = [("haydar", "0"), ("obur chef", "0119195"), ("cig kofte", "0119195"), ("cigkofte", "0119195"), ("icli kofte", "0119195"),
         ("sarma", "0119195"), ("dolma", "0119195"),
         ("salata", "0119195"), ("*", "0")]
_FIRIN = [("kekik", "0111311"), ("kruvasan", "0111392"), ("donut", "0111392"),
          ("kek", "0111392"),
          ("pasta", "0111392"), ("ekler", "0111392"), ("sekerpare", "0111392"),
          ("halka tatli", "0111392"), ("baklavalik", "0"), ("baklava", "0111398"), ("kedi dili", "0111393"),
          ("cookie", "0111393"), ("kurabiye", "0111393"),
          ("grissini", "0111394"), ("grissuno", "0111394"), ("kitiruno", "0111394"),
          ("galeta", "0111394"), ("peksimet", "0111394"),
          ("kadayif", "0"), ("kadaf", "0"), ("yufka", "0"), ("kekik", "0111311"),
          ("simit", "0111399"), ("pogaca", "0111399"), ("acma", "0111399"),
          ("corek", "0111399"), ("coreg", "0111399"), ("borek", "0111399"),
          ("boreg", "0111399"), ("pide", "0111311"),
          ("ekme", "0111311"), ("lavas", "0111311"), ("tortilla", "0111311"),
          ("hamburger", "0111311"), ("sandvic", "0111311"), ("denge", "0111311"),
          ("tava", "0111311"), ("bugday", "0111311"), ("tahilli", "0111311"),
          ("*", "0")]

SUBCAT_RULES = {
    # --- Çay, şeker, bakliyat, un, makarna ---
    "Dökme Çaylar": [("*", "0123021")],
    "Poşet Çaylar": [("*", "0123021")],
    "Bitki Çayları": [("*", "0123021")],
    "Küp Şeker": [("*", "0118122")],
    "Toz Şeker Paket": [("kup", "0118122"), ("pudra", "0"), ("esmer", "0"),
                        ("*", "0118121")],
    "Klasik Makarnalar": _MAKARNA,
    "Özel Makarnalar": _MAKARNA,
    "Klasik Un": [("nohut", "0"), ("karabugday", "0"), ("mercimek", "0"), ("*", "0111211")],
    "Karışım Un": [("galeta", "0"), ("pirinc", "0"), ("misir", "0"), ("nohut", "0"),
                   ("glutensiz", "0"), ("karisim", "0"), ("kepeg", "0"), ("yulaf", "0"),
                   ("cavdar", "0"), ("*", "0111211")],
    "Bakliyat Paket": [("pilaki", "0119195"), ("pirinc", "0111121"), ("pirnc", "0111121"),
                       ("borulce", "0117611"), ("bulgur", "0111192"),
                       ("fasulye", "0117611"), ("barbunya", "0117611"),
                       ("nohut", "0117632"), ("mercimek", "0117643"), ("*", "0")],
    "Tuz": [("limon tuzu", "0"), ("*", "0119311")],
    "Kabartma - Vanilin - Maya": [("jole", "0119904"), ("kabartma", "0119902"), ("maya", "0119902"),
                                  ("karbonat", "0119902"), ("*", "0")],
    "Harçlar - Toz Soslar": [("harc", "0119402"), ("cesni", "0119402"),
                             ("baharat", "0119402"), ("*", "0")],
    "Toz Tatlı - Kek Yap": [("puding", "0119904"), ("muhallebi", "0119904"),
                            ("santi", "0119904"), ("krem santi", "0119904"),
                            ("jole", "0119904"), ("sutlac", "0119904"),
                            ("kazandibi", "0119904"), ("pastaci kremasi", "0119904"),
                            ("supangle", "0119904"), ("keskul", "0119904"),
                            ("tavuk gogsu", "0119904"), ("tavukgogsu", "0119904"),
                            ("pud", "0119904"), ("jel", "0119904"), ("pasta krem", "0119904"),
                            ("creme ole", "0119904"), ("cool dream", "0119904"),
                            ("profiterol", "0119904"), ("trilece", "0119904"),
                            ("irmik tatlisi", "0119904"), ("asure", "0119904"),
                            ("kabartma", "0119902"),
                            ("maya", "0119902"), ("*", "0")],
    "Puding Grubu": [("pud", "0119904"), ("yogotella", "0119904"),
                     ("kasik tatlisi", "0119904"), ("*", "0")],
    "Baharat Paket": [("karbonat", "0119902"), ("limon tuzu", "0"),
                      ("kus uzum", "0116711"), ("hindistan cevizi", "0"), ("h cevizi", "0"),
                      ("ever well", "0"), ("unu", "0"), ("keten", "0"), ("pasta susu", "0"),
                      ("deniz tuzu", "0119311"), ("ihlamur", "0123021"),
                      ("adacay", "0123021"), ("*", "0119402")],
    "(Organık urunler)": [("pekmez", "0118397"), ("tahin", "0118408"),
                          ("tuz", "0119311"), ("sirke", "0119393"),
                          ("elma suyu", "0121001"), ("pirinc unu", "0"),
                          ("galeta", "0"), ("yulaf", "0111401"), ("pirinc", "0111121"),
                          ("bulgur", "0111192"), ("mercimek", "0117643"),
                          ("fasulye", "0117611"), ("un", "0111211"), ("*", "0")],
    # --- içecekler ---
    "Kola Grubu": [("*", "0126003")],
    "Sade Gazozlar": [("*", "0126002")],
    "Meyveli Gazozlar": [("soda", "0125002"), ("maden", "0125002"), ("*", "0126002")],
    "Sade Soda": [("*", "0125002")],
    "Meyveli Soda": [("efsane", "0126002"), ("*", "0125002")],
    "Meyve Suları": _ICECEK,
    "Gazsız İçecekler": _ICECEK,
    "Enerji İçecekleri": [("*", "0126002")],
    "Şalgam Suyu": [("*", "0")],
    "Toz İçecekler": [("*", "0")],
    "Su": [("maden", "0125002"), ("soda", "0125002"), ("*", "0125001")],
    # --- çorba, yağ, margarin ---
    "Klasik Çorbalar": [("kemik", "0"), ("tavuk suyu", "0"), ("*", "0119161")],
    "Özel Çorbalar": [("*", "0")],
    "Bulyon Grubu": [("*", "0")],
    "Ayçiçek Yağları": [("*", "0115112")],
    "Mısırözü Yağları": [("*", "0")],
    "Zeytin Yağları": [("*", "0115131")],
    "Fındık Yağları": [("*", "0")],
    "Margarin Kase": [("surmix", "0"), ("*", "0115301")],
    "Margarin Paket": [("*", "0115301")],
    # --- konserve, sos, unlu mamul ---
    "Balık Konserve": [("*", "0113315")],
    "Sebze Konserve": [("domates suyu", "0121001"), ("pilav", "0119195"),
                       ("kisir", "0119195"), ("hazir salata", "0119195"),
                       ("salatasi", "0119195"), ("pilaki", "0119195"), ("asurelik", "0"),
                       ("tursu", "0117992"), ("biber salca", "0"), ("salca", "0117995"),
                       ("*", "0117923")],
    "Hazır Yemek Konserve": [("*", "0119195")],
    "Salçalar": [("biber", "0"), ("menemen", "0"), ("rende", "0117923"),
                 ("puresi", "0117923"), ("*", "0117995")],
    "Turşu Konserveler": [("sos", "0"), ("*", "0117992")],
    "Ketçap - Mayonez": [("ketcap+mayonez", "0"), ("ketcap", "0119396"),
                         ("mayonez", "0119397"), ("*", "0")],
    "Sirke - Limon Sosları": [("sirke", "0119393"), ("*", "0")],
    "Sos Konserve": [("dolmasi", "0119195"), ("pilav", "0119195"), ("pilaki", "0119195"),
                     ("tursu", "0117992"), ("domates rende", "0117923"), ("dogranmis domates", "0117923"),
                     ("ketcap", "0119396"), ("mayonez", "0119397"), ("*", "0")],
    "Unlu Mamüller": _FIRIN,
    "Hazır Tatlılar": [("2 5 yagli", "0114201"), ("sut", "0114111")] + _SEBZE_MEYVE[:-1] + [("ekmek", "0111311"),
                                                                 ("*", "0")],
    "Konserve - Soslar - Unlu Mamüller": _FIRIN,
    # --- atıştırmalık ---
    "Bisküviler": _BISKUVI,
    "Diyet Bisküvi": [("bar", "0"), ("freeze dry", "0"), ("mixmey", "0")] + _BISKUVI,
    "Hazır Kekler": [("bisk", "0111393"), ("gofret", "0111396"), ("*", "0111392")],
    "Çikolatalar": _CIKOLATA,
    "Kaplamalı Ürünler - Gofretler": _CIKOLATA,
    "Bayramlık Çikolata": _CIKOLATA,
    "Bayramlık Şeker": [("*", "0118995")],
    "Pure Mamalar": [("*", "0")],
    "Kutu Toz Mamalar": [("kasik", "0"), ("junior", "0"), ("ml", "0"), ("*", "0119212")],
    "Cipsler": [("popzz", "0117998"), ("noutos", "0"), ("patlak", "0"), ("fisti", "0116886"), ("patlamis", "0"), ("popcorn", "0"), ("*", "0117998")],
    "Kuruyemiş Paket": [("bar", "0"), ("hindistan", "0"), ("lokma", "0"), ("krokan", "0"),
                        ("haribo", "0118995"), ("kara simsek", "0116898"),
                        ("citliyo", "0116898"), ("gun kurusu", "0116793"), ("leblebi sekeri", "0"), ("karisik", "0"),
                        ("kokteyl", "0"), ("favori", "0"), ("kaju", "0"),
                        ("kayisi", "0116793"), ("kuru uzum", "0116711"),
                        ("uzum", "0116711"), ("hurma", "0116791"),
                        ("antep fisti", "0116854"), ("fisti", "0116886"),
                        ("ceviz", "0116862"), ("badem", "0116811"), ("findik", "0116843"),
                        ("kabak cekirdeg", "0116891"), ("leblebi", "0116897"),
                        ("cekirdek", "0116898"), ("aycekirdeg", "0116898"), ("*", "0")],
    "Türk Kahveleri": [("salep", "0"), ("sicak cikolata", "0"), ("*", "0122011")],
    "3 in 1 Kahveler": [("*", "0122012")],
    "Instant Kahveler": [("soguk kahve", "0"), ("krema", "0"), ("filtre", "0122011"),
                         ("cekirdek", "0122011"), ("kapsul", "0122011"),
                         ("turk kahve", "0122011"), ("*", "0122012")],
    "Kahve Kremaları": [("*", "0")],
    "Sakızlar": [("lolipop", "0118995"), ("bebeto", "0118995"), ("sipsevdi", "0118995"),
                 ("*", "0118994")],
    "Şekerler": [("ever well", "0"), ("kayisi", "0116793"), ("lokum", "0118991"), ("pestil", "0"),
                 ("cevizli sucuk", "0"), ("pismaniye", "0"), ("cezerye", "0"),
                 ("sakiz", "0118994"), ("*", "0118995")],
    "Fındık Fıstık Ezmeleri": [("yer fist", "0"), ("fistik ezme", "0"), ("kakao", "0118593"),
                               ("nutella", "0118593"), ("krem", "0118593"),
                               ("findik ezme", "0118401"), ("*", "0")],
    "Kakaolu Fındık Kremaları": [("yer fist", "0"), ("fistik ezme", "0"), ("kakao", "0118593"),
                                 ("bitter", "0118593"), ("krem", "0118593"),
                                 ("findik ezme", "0118401"), ("*", "0118593")],
    "Kahvaltılık - Gevrekler": [("bar", "0"), ("patla", "0"), ("grissini", "0111394"),
                                ("*", "0111401")],
    "Sıcak Çikolata - Salep - Granül": [("nescafe", "0122012"), ("*", "0")],
    # --- yoğurt, ayran, donuk, yumurta, dondurma ---
    "Doğal Yoğurtlar": [("*", "0114601")],
    "Kaymaklı Yoğurtlar": [("*", "0114601")],
    "Meyveli Yoğurtlar": [("puding", "0114701"), ("danissimo", "0114701"),
                          ("*", "0114601")],
    "Çocuk Grubu": [("puding", "0114701"), ("milkshake", "0114703"), ("*", "0114601")],
    "Special Grup": [("*", "0114601")],
    "Sağlık Grubu": [("kefir", "0"), ("shot", "0"), ("shake", "0"), ("nilky", "0"),
                     ("probiyotik", "0"), ("*", "0114601")],
    "Büyük Boy Ayranlar": [("kefir", "0"), ("*", "0114605")],
    "Küçük Boy Ayranlar": [("kefir", "0"), ("*", "0114605")],
    "Donuk Et-Balık-Tavuk": [("pilic", "0112590"), ("tavuk", "0112590"),
                             ("kofte+blk", "0"), ("kofte", "0112593"),
                             ("burger", "0112593"), ("turk somon", "0113191"),
                             ("somon+fileto", "0113121"), ("hamsi", "0113191"),
                             ("uskumru", "0113191"), ("mezgit", "0113191"),
                             ("cipura", "0113191"), ("levrek", "0113191"),
                             ("palamut", "0113151"), ("*", "0")],
    "Donuk Balık": _PEYNIR,
    "Donuk Sebze - Meyve": [("lahmacun", "0119195"), ("*", "0")],
    "Donuk Hamur": [("su boreg", "0119192"), ("pizza", "0119145"), ("napoliten", "0119145"),
                    ("milfoy", "0"), ("hamuru", "0"), ("baklava", "0111398"),
                    ("simit", "0111399"), ("pogaca", "0111399"), ("ristorante", "0119145"),
                    ("tavuk burger", "0112590"), ("hamburger", "0112593"),
                    ("boreg", "0119195"), ("coreg", "0111392"), ("kunefe", "0111392"),
                    ("kadayif", "0111392"), ("katmer", "0111392"), ("mac", "0119195"),
                    ("falafel", "0119195"), ("tost", "0119195"),
                    ("pasta", "0111392"), ("trilece", "0111392"), ("sufle", "0111392"),
                    ("ekler", "0111392"), ("turta", "0111392"), ("corek", "0111392"),
                    ("tatl", "0111392"), ("simit", "0111399"), ("pogaca", "0111399"),
                    ("burger", "0112593"), ("borek", "0119195"), ("manti", "0119195"),
                    ("pelmeni", "0119195"), ("lahmacun", "0119195"), ("pide", "0119195"),
                    ("etli ekmek", "0119195"), ("lazanya", "0119195"),
                    ("*", "0")],
    "İler İşlenmiş Kg": [("*", "0112590")],
    "İleri İŞlenmiş Paket": [("pilic", "0112590"), ("doner", "0112593"), ("*", "0")],
    "Normal Yumurtalar": [("*", "0114811")],
    "Özel Yumurtalar": [("*", "0114811")],
    "Büyük Boy Dondurmalar": [("*", "0118601")],
    "Küçük Boy Dondurmalar": [("*", "0118601")],
    "Paket Zeytinler": [("salata", "0"), ("*", "0117476")],
    "Yoğurt - Dondurma": [("*", "0114701")],
    # --- süt ürünleri ---
    "Süt UHT": _SUT,
    "1/5 UHT Aromalı ve Sade Sütler": _SUT,
    "Salep - Sıvı Krema": [("salep", "0114703"), ("bitkisel", "0"),
                           ("pasta kremasi", "0119904"), ("sos", "0"), ("pesto", "0"),
                           ("*", "0114331")],
    "Paket Peynir": _PEYNIR,
    "Paket Kaşar": _PEYNIR,
    "Paket Yöresel Peynir": _PEYNIR,
    "Kaşar Peynir KG": _PEYNIR,
    "İthal Peynirler": _PEYNIR,
    "Beyaz Peynir KG": _PEYNIR,
    "Yöresel Peynir KG": _PEYNIR,
    "Tereyağ Paket": [("peynir", "0114501"), ("sade yag", "0"), ("*", "0115211")],
    "Tereyağ KG": [("*", "0115211")],
    "Kaymak Paket": [("*", "0114331")],
    # --- manav ---
    "Meyve": _SEBZE_MEYVE,
    "Sebze": _SEBZE_MEYVE,
    # --- kahvaltılık ---
    "Helva KG": [("*", "0118916")],
    "Helva Paket": [("dondurma", "0"), ("kornet", "0"), ("pismaniye", "0"),
                    ("kagit helva", "0"), ("*", "0118916")],
    "Bal Paket": [("apitera", "0"), ("*", "0118313")],
    "Bal Kg": [("*", "0118313")],
    "Reçel": [("*", "0118391")],
    "Tahin": [("tahin+pekmez", "0"), ("kakaolu findik", "0118593"),
              ("pekmez", "0118397"), ("tahin", "0118408"), ("*", "0")],
    "Salam KG Dana": _SARKUTERI, "Salam KG Piliç": _SARKUTERI,
    "Salam KG Hindi": _SARKUTERI, "Salam KG Karışım": _SARKUTERI,
    "Salam Paket Dana": _SARKUTERI, "Salam Paket Piliç": _SARKUTERI,
    "Salam Paket Hindi": _SARKUTERI, "Salam Paket Karışım": _SARKUTERI,
    "Sucuk KG Dana": _SARKUTERI, "Sucuk KG Piliç": _SARKUTERI,
    "Sucuk KG Karışım": _SARKUTERI, "Sucuk Paket Dana": _SARKUTERI,
    "Sucuk Paket Piliç": _SARKUTERI, "Sucuk Paket Hindi": _SARKUTERI,
    "Sucuk Paket Karışım": _SARKUTERI,
    "Sosis Dana": _SARKUTERI, "Sosis Piliç": _SARKUTERI, "Sosis Karışım": _SARKUTERI,
    "Kavurma": _SARKUTERI,
    "Pastırma KG": _SARKUTERI, "Pastırma Paket": _SARKUTERI,
    # --- kasap, şarküter, açık ürünler ---
    "Dana KG": [("*", "0112214")],
    "Kuzu KG": [("pilic", "0112246"), ("*", "0112230")],
    "Piliç KG": [("ciger", "0112401"), ("*", "0112246")],
    "Hindi KG": [("pilic", "0112246"), ("*", "0")],
    "Kuruyemiş KG": [("petek bal", "0118313"), ("hurma", "0116791"), ("cay", "0123021"),
                     ("ihlamur", "0123021"),
                     ("*", "0")],
    "Kuruyemiş KG Sitoğlu": [("*", "0")],
    "Baharat KG": [("*", "0")],
    "Açık Zeytinler": [("*", "0117476")],
    "Pet Grubu Paket Zeytinler": [("salata", "0"), ("*", "0117476")],
    "Erişte - Mantı": [("kofte", "0112593"), ("tarhana", "0"), ("eriste", "0111501"),
                       ("*", "0119195")],
    "Yufka - Bazlama": [("hurma", "0116791"), ("*", "0")],
    "Ekmek": _FIRIN,
    "Pastane KG": [("*", "0")],
    "Lokum KG": [("cikolata kapli helva", "0"), ("pismaniye", "0"), ("helva", "0"),
                 ("lokum", "0118991"), ("cikolata", "0118512"), ("jelibon", "0118995"),
                 ("cakil", "0118995"),
                 ("seker", "0118995"), ("*", "0")],
    "EMIN PAST.SLM": [("zeytin", "0117476"), ("lavas", "0111311"), ("*", "0")],
    "Turşu KG": [("*", "0117992")],
    "Turşu Paket": [("*", "0117992")],
    "Bakliyat KG": [("pirinc", "0111121"), ("bulgur", "0111192"), ("fasulye", "0117611"),
                    ("nohut", "0117632"), ("mercimek", "0117643"), ("*", "0")],
    "Çiğköfte": _MEZE,
    "Meze": _MEZE,
}
_RULES = {norm(k): v for k, v in SUBCAT_RULES.items()}


def _kw_in(kw, padded_name):
    return all(f" {part}" in padded_name for part in kw.split("+"))


def assign_subcategory(leaf_category, product_name):
    """Ürünün TÜİK 7 haneli kodunu döndürür; karşılık yoksa '0'."""
    rules = _RULES.get(norm(leaf_category))
    if not rules:
        return "0"
    padded = f" {norm(product_name)}"
    for kw, code in rules:
        if kw == "*" or _kw_in(kw, padded):
            return code
    return "0"


# ---------- sayfa okuma ----------
def parse_reyons(page, page_url):
    """'Reyon Seçiniz' listesi: [(tam adres, ad), ...]"""
    m = re.search(r'<ul class="dropdown-menu" aria-labelledby="dropdownMenu1">(.*?)</ul>', page, re.S)
    if not m:
        return []
    out = []
    for href, text in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S):
        name = clean(text)
        if name:
            out.append((urljoin(page_url, html.unescape(href)), name))
    return list(dict.fromkeys(out))


def parse_last_page(page):
    nums = [int(n) for n in re.findall(r'href="\?page=(\d+)"', page)]
    return max(nums) if nums else 1


def parse_products(page):
    products = []
    for chunk in page.split('<div class="desktop-product-card"')[1:]:
        id_m = re.search(r'id="productCard\w*?(\d+)"', chunk)
        name_m = re.search(r'<p class="desktop-product-name">\s*<a href="([^"]+)"[^>]*>(.*?)</a>',
                           chunk, re.S)
        price_m = re.search(r'<p class="desktop-product-price">(.*?)</p>', chunk, re.S)
        img_m = re.search(r'<img[^>]+class="img-product[^"]*"[^>]+src="([^"]+)"', chunk)
        if not name_m or not price_m:
            continue
        prices = re.findall(r"(\d[\d.]*,\d{2})\s*TL", price_m.group(1))
        products.append({
            "id": id_m.group(1) if id_m else name_m.group(1),
            "name": clean(name_m.group(2)),
            "url": urljoin(BASE, html.unescape(name_m.group(1))),
            "image_url": urljoin(BASE, html.unescape(img_m.group(1))) if img_m else "",
            # Birden fazla fiyat görünürse (eski + indirimli) sonuncusu güncel fiyattır
            "price": to_float(prices[-1]) if prices else None,
            "all_prices": " | ".join(prices),
        })
    return products


def fetch_category(url, first_page=None):
    """Bir reyonun tüm sayfalarını okur. (ürünler, son sayfa no)"""
    products, seen = [], set()
    page = first_page or get_html(url)
    if page is None:
        return [], 0
    last = parse_last_page(page)
    for page_no in range(1, min(last, MAX_PAGES) + 1):
        if page_no > 1:
            time.sleep(SLEEP)
            page = get_html(url, {"page": page_no})
            if page is None:
                break
        new = [p for p in parse_products(page) if p["id"] not in seen]
        if not new:
            break
        for p in new:
            seen.add(p["id"])
            products.append(p)
    return products, last


def count_products(url, first_page, last):
    """Reyonun sitedeki ürün sayısı: (son sayfa - 1) x sayfa başı + son sayfadaki ürün."""
    first = parse_products(first_page)
    if last <= 1:
        return len(first)
    time.sleep(SLEEP)
    last_page = get_html(url, {"page": last})
    if last_page is None:
        return None
    return (last - 1) * len(first) + len(parse_products(last_page))


# ---------- kategori ağacı ----------
def walk(url, path, depth, visited, rows, cat_log):
    """Reyonu alt reyonlarına kadar iner. Alt reyonu olmayan reyonun ürünleri okunur.
    Bu reyonun altında görülen tüm ürün ID'lerini döndürür."""
    leaf_name = path.split(" > ")[-1]
    visited.add(norm(leaf_name))
    if has_kw(leaf_name, EXCLUDE):
        cat_log.append({"secildi": False, "path": path, "url": url, "sayfa": None,
                        "okunan": 0, "yeni": 0, "neden": "gıda dışı"})
        print(f"  - atlandı: {path}")
        return set()

    page = get_html(url)
    if page is None:
        cat_log.append({"secildi": True, "path": path, "url": url, "sayfa": None,
                        "okunan": 0, "yeni": 0, "neden": "sayfa açılmadı"})
        return set()
    children = [(u, n) for u, n in parse_reyons(page, url) if norm(n) not in visited]
    if depth >= MAX_DEPTH:
        children = []

    subtree_ids = set()
    if children:
        for _, n in children:          # kardeş reyonlar tekrar alt reyon sanılmasın
            visited.add(norm(n))
        for u, n in children:
            time.sleep(SLEEP)
            subtree_ids |= walk(u, f"{path} > {n}", depth + 1, visited, rows, cat_log)
        if not CHECK_PARENT_PRODUCTS:
            return subtree_ids
        last = parse_last_page(page)
        on_site = count_products(url, page, last)
        # Sadece sayılar birebir eşitse atla. Alt reyonlarda üst reyonda görünmeyen ürünler
        # de olabildiği için "küçük eşit" güvenli değil (Yoğurt - Dondurma: 635 / 637).
        if on_site is not None and on_site == len(subtree_ids):
            cat_log.append({"secildi": True, "path": path, "url": url, "sayfa": last,
                            "okunan": 0, "yeni": 0,
                            "neden": f"üst reyon, sitede {on_site} / alt reyonlarda {len(subtree_ids)}"})
            print(f"  {path}: alt reyonlar kapsıyor ({on_site} / {len(subtree_ids)}), tekrar okunmadı")
            return subtree_ids
        print(f"  {path}: sitede {on_site}, alt reyonlarda {len(subtree_ids)} -> üst reyon okunuyor")

    products, last = fetch_category(url, first_page=page)
    subtree_ids |= {p["id"] for p in products}
    added = 0
    for p in products:
        if p["id"] in rows or p["price"] is None:
            continue
        rows[p["id"]] = {**p, "path": path, "leaf": leaf_name}
        added += 1
    kind = "üst reyon" if children else ""
    cat_log.append({"secildi": True, "path": path, "url": url, "sayfa": last,
                    "okunan": len(products), "yeni": added, "neden": kind})
    print(f"  {path}: {last} sayfa, {len(products)} ürün, {added} yeni"
          f"{'  (üst reyon)' if children else ''}")
    return subtree_ids


def get_start_groups():
    page = get_html(BASE + "/")
    if page is None:
        raise SystemExit("Ana sayfa alınamadı.")
    groups = []
    for href in re.findall(r'<a[^>]+href="([^"]+)"', page):
        full = urljoin(BASE, html.unescape(href))
        parts = unquote(urlparse(full).path).strip("/").split("/")
        if len(parts) >= 2 and parts[0] in FOOD_ROOTS:
            groups.append((full, " > ".join(p.replace("_", " ") for p in parts)))
    groups = list(dict.fromkeys(groups))
    # Önce iki seviyeli gruplar, sonra menüde ayrıca verilen derin linkler (ör. Bebek Gıdası)
    return sorted(groups, key=lambda g: g[1].count(">"))
