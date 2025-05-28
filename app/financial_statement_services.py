from app.models import YevmiyeMaddesiBasligi, YevmiyeFisiSatiri, Firma # Firma import edildi
from sqlalchemy import func, and_
from app import db
from collections import defaultdict
from datetime import date
import logging

logger = logging.getLogger(__name__)

# HESAP PLANI EŞLEŞTİRME VE NİTELİKLERİ
# normal_balance: 'D' (Debit/Borç), 'C' (Credit/Alacak)
# fs_impact: Mali tabloda toplama nasıl etki edeceği (1: pozitif, -1: negatif)
#            Örn: Satış İndirimleri (610) normalde Borç bakiyesi verir ama Net Satışları azaltır.
#            Maliyet ve Gider hesapları Borç bakiyesi verir ama Karı azaltır.
HESAP_DETAYLARI = {
    # DÖNEN VARLIKLAR (Genellikle Borç Bakiyesi Verir, Bilançoda Pozitif)
    '100': {'adi': 'KASA', 'grup': 'HAZIR_DEGERLER', 'fs_kalem': 'DONEN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '101': {'adi': 'ALINAN ÇEKLER', 'grup': 'HAZIR_DEGERLER', 'fs_kalem': 'DONEN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '102': {'adi': 'BANKALAR', 'grup': 'HAZIR_DEGERLER', 'fs_kalem': 'DONEN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '120': {'adi': 'ALICILAR', 'grup': 'TICARI_ALACAKLAR', 'fs_kalem': 'DONEN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '121': {'adi': 'ALACAK SENETLERİ', 'grup': 'TICARI_ALACAKLAR', 'fs_kalem': 'DONEN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '153': {'adi': 'TİCARİ MALLAR', 'grup': 'STOKLAR', 'fs_kalem': 'DONEN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '190': {'adi': 'DEVREDEN KDV', 'grup': 'DIGER_DONEN_VARLIKLAR', 'fs_kalem': 'DONEN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '191': {'adi': 'İNDİRİLECEK KDV', 'grup': 'DIGER_DONEN_VARLIKLAR', 'fs_kalem': 'DONEN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    
    # DURAN VARLIKLAR (Genellikle Borç Bakiyesi Verir, Bilançoda Pozitif)
    # Örnek olarak birkaçı:
    '252': {'adi': 'BİNALAR', 'grup': 'MADDI_DURAN_VARLIKLAR', 'fs_kalem': 'DURAN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '255': {'adi': 'DEMİRBAŞLAR', 'grup': 'MADDI_DURAN_VARLIKLAR', 'fs_kalem': 'DURAN_VARLIKLAR', 'normal_balance': 'D', 'fs_impact': 1},
    '257': {'adi': 'BİRİKMİŞ AMORTİSMANLAR', 'grup': 'MADDI_DURAN_VARLIKLAR_INDIRIM', 'fs_kalem': 'DURAN_VARLIKLAR', 'normal_balance': 'C', 'fs_impact': -1}, # (-) Aktifi azaltır

    # KISA VADELİ YABANCI KAYNAKLAR (Genellikle Alacak Bakiyesi Verir, Bilançoda Pozitif)
    '300': {'adi': 'BANKA KREDİLERİ (KV)', 'grup': 'MALI_BORCLAR_KV', 'fs_kalem': 'KVYK', 'normal_balance': 'C', 'fs_impact': 1},
    '320': {'adi': 'SATICILAR', 'grup': 'TICARI_BORCLAR_KV', 'fs_kalem': 'KVYK', 'normal_balance': 'C', 'fs_impact': 1},
    '360': {'adi': 'ÖDENECEK VERGİ VE FONLAR', 'grup': 'ODENECEK_VERGI_VE_DIGER_YUKUMLULUKLER_KV', 'fs_kalem': 'KVYK', 'normal_balance': 'C', 'fs_impact': 1},
    '391': {'adi': 'HESAPLANAN KDV', 'grup': 'ODENECEK_VERGI_VE_DIGER_YUKUMLULUKLER_KV', 'fs_kalem': 'KVYK', 'normal_balance': 'C', 'fs_impact': 1},

    # UZUN VADELİ YABANCI KAYNAKLAR (Genellikle Alacak Bakiyesi Verir, Bilançoda Pozitif)
    '400': {'adi': 'BANKA KREDİLERİ (UV)', 'grup': 'MALI_BORCLAR_UV', 'fs_kalem': 'UVYK', 'normal_balance': 'C', 'fs_impact': 1},

    # ÖZKAYNAKLAR (Genellikle Alacak Bakiyesi Verir, Bilançoda Pozitif)
    '500': {'adi': 'SERMAYE', 'grup': 'ODENMIS_SERMAYE', 'fs_kalem': 'OZKAYNAKLAR', 'normal_balance': 'C', 'fs_impact': 1},
    '570': {'adi': 'GEÇMİŞ YILLAR KARLARI', 'grup': 'GECMIS_YILLAR_KARLARI_ZARARLARI', 'fs_kalem': 'OZKAYNAKLAR', 'normal_balance': 'C', 'fs_impact': 1},
    '580': {'adi': 'GEÇMİŞ YILLAR ZARARLARI', 'grup': 'GECMIS_YILLAR_KARLARI_ZARARLARI', 'fs_kalem': 'OZKAYNAKLAR', 'normal_balance': 'D', 'fs_impact': -1}, # (-) Özkaynakları azaltır
    '590': {'adi': 'DÖNEM NET KARI', 'grup': 'DONEM_NET_KARI_ZARARI', 'fs_kalem': 'OZKAYNAKLAR', 'normal_balance': 'C', 'fs_impact': 1},
    '591': {'adi': 'DÖNEM NET ZARARI', 'grup': 'DONEM_NET_KARI_ZARARI', 'fs_kalem': 'OZKAYNAKLAR', 'normal_balance': 'D', 'fs_impact': -1}, # (-) Özkaynakları azaltır

    # GELİR TABLOSU HESAPLARI
    '600': {'adi': 'YURTİÇİ SATIŞLAR', 'grup': 'BRUT_SATISLAR', 'fs_kalem': 'GELIR_TABLOSU_GELIR', 'normal_balance': 'C', 'fs_impact': 1},
    '601': {'adi': 'YURTDIŞI SATIŞLAR', 'grup': 'BRUT_SATISLAR', 'fs_kalem': 'GELIR_TABLOSU_GELIR', 'normal_balance': 'C', 'fs_impact': 1},
    '610': {'adi': 'SATIŞTAN İADELER', 'grup': 'SATIS_INDIRIMLERI', 'fs_kalem': 'GELIR_TABLOSU_GIDER_INDIRIM', 'normal_balance': 'D', 'fs_impact': -1}, # (-)
    '611': {'adi': 'SATIŞ İSKONTOLARI', 'grup': 'SATIS_INDIRIMLERI', 'fs_kalem': 'GELIR_TABLOSU_GIDER_INDIRIM', 'normal_balance': 'D', 'fs_impact': -1}, # (-)
    '620': {'adi': 'SATILAN MAMÜLLER MALİYETİ', 'grup': 'SATISLARIN_MALIYETI', 'fs_kalem': 'GELIR_TABLOSU_GIDER_INDIRIM', 'normal_balance': 'D', 'fs_impact': -1}, # (-)
    '621': {'adi': 'SATILAN TİCARİ MALLAR MALİYETİ', 'grup': 'SATISLARIN_MALIYETI', 'fs_kalem': 'GELIR_TABLOSU_GIDER_INDIRIM', 'normal_balance': 'D', 'fs_impact': -1}, # (-)
    '632': {'adi': 'GENEL YÖNETİM GİDERLERİ (Yansıtılan)', 'grup': 'FAALIYET_GIDERLERI', 'fs_kalem': 'GELIR_TABLOSU_GIDER_INDIRIM', 'normal_balance': 'D', 'fs_impact': -1}, # (-)
    '642': {'adi': 'FAİZ GELİRLERİ', 'grup': 'DIGER_FAALIYET_GELIR_KAR', 'fs_kalem': 'GELIR_TABLOSU_GELIR', 'normal_balance': 'C', 'fs_impact': 1},
    '660': {'adi': 'KISA VADELİ BORÇLANMA GİDERLERİ', 'grup': 'FINANSMAN_GIDERLERI', 'fs_kalem': 'GELIR_TABLOSU_GIDER_INDIRIM', 'normal_balance': 'D', 'fs_impact': -1}, # (-)
    '770': {'adi': 'GENEL YÖNETİM GİDERLERİ', 'grup': '_MALIYET_HESABI', 'fs_kalem': '_MALIYET_HESABI', 'normal_balance': 'D', 'fs_impact': 1}, # Yansıtma öncesi
    # ... diğer hesaplar ve daha detaylı gruplamalar eklenebilir ...
}

# Ana Mali Tablo Kalemlerini Tanımlama (HESAP_PLANI_MAP'teki fs_kalem ve grup anahtarlarına göre)
BILANCO_YAPISI = {
    "AKTIFLER": {
        "I. DÖNEN VARLIKLAR": ['HAZIR_DEGERLER', 'MENKUL_KIYMETLER', 'TICARI_ALACAKLAR', 'STOKLAR', 'DIGER_DONEN_VARLIKLAR'],
        "II. DURAN VARLIKLAR": ['TICARI_ALACAKLAR_DV', 'MADDI_DURAN_VARLIKLAR', 'MADDI_OLMAYAN_DURAN_VARLIKLAR', 'OZEL_TUKENMEYE_TABI_VARLIKLAR']
    },
    "PASIFLER": {
        "III. KISA VADELİ YABANCI KAYNAKLAR": ['MALI_BORCLAR_KV', 'TICARI_BORCLAR_KV', 'DIGER_BORCLAR_KV', 'ALINAN_AVANSLAR_KV', 'ODENECEK_VERGI_VE_DIGER_YUKUMLULUKLER_KV', 'BORC_VE_GIDER_KARSILIKLARI_KV'],
        "IV. UZUN VADELİ YABANCI KAYNAKLAR": ['MALI_BORCLAR_UV', 'TICARI_BORCLAR_UV'],
        "V. ÖZKAYNAKLAR": ['ODENMIS_SERMAYE', 'SERMAYE_YEDEKLERI', 'KAR_YEDEKLERI', 'GECMIS_YILLAR_KARLARI_ZARARLARI', 'DONEM_NET_KARI_ZARARI']
    }
}

GELIR_TABLOSU_YAPISI = [ # Sıralı olması önemli
    ('A. BRÜT SATIŞLAR', ['BRUT_SATISLAR'], 1),
    ('B. SATIŞ İNDİRİMLERİ (-)', ['SATIS_INDIRIMLERI'], -1),
    ('NET SATIŞLAR', [], 0, lambda gt: gt.get('A. BRÜT SATIŞLAR',0) - gt.get('B. SATIŞ İNDİRİMLERİ (-)',0)), # Hesaplama fonksiyonu
    ('C. SATIŞLARIN MALİYETİ (-)', ['SATISLARIN_MALIYETI'], -1),
    ('BRÜT SATIŞ KÂRI (ZARARI)', [], 0, lambda gt: gt.get('NET SATIŞLAR',0) - gt.get('C. SATIŞLARIN MALİYETİ (-)',0)),
    ('D. FAALİYET GİDERLERİ (-)', ['FAALIYET_GIDERLERI'], -1), # Bu kendi içinde alt toplamları olan bir grup olabilir
    ('ESAS FAALİYET KÂRI (ZARARI)', [], 0, lambda gt: gt.get('BRÜT SATIŞ KÂRI (ZARARI)',0) - gt.get('D. FAALİYET GİDERLERİ (-)',{}).get('TOPLAM',0)),
    ('E. DİĞER FAALİYETLERDEN OLAĞAN GELİR VE KÂRLAR', ['DIGER_FAALIYET_GELIR_KAR'], 1),
    ('F. DİĞER FAALİYETLERDEN OLAĞAN GİDER VE ZARARLAR (-)', ['DIGER_FAALIYET_GIDER_ZARARLAR'], -1),
    ('OLAĞAN KÂR (ZARAR)', [], 0, lambda gt: gt.get('ESAS FAALİYET KÂRI (ZARARI)',0) + gt.get('E. DİĞER FAALİYETLERDEN OLAĞAN GELİR VE KÂRLAR',0) - gt.get('F. DİĞER FAALİYETLERDEN OLAĞAN GİDER VE ZARARLAR (-)',0)),
    ('G. FİNANSMAN GİDERLERİ (-)', ['FINANSMAN_GIDERLERI'], -1),
    ('SÜRDÜRÜLEN FAALİYETLER VERGİ ÖNCESİ KÂRI (ZARARI)', [], 0, lambda gt: gt.get('OLAĞAN KÂR (ZARAR)',0) - gt.get('G. FİNANSMAN GİDERLERİ (-)',0)),
    # ... (Vergi ve Net Kar/Zarar hesaplamaları)
]


def get_hesap_bakiyeleri_for_period(firma_id: int, donem_baslangic_date: date, donem_bitis_date: date):
    """
    Belirtilen firma ve dönem aralığı için hesapların net hareketlerini veya dönem sonu bakiyelerini hesaplar.
    Yevmiye Defteri'nden hareketleri alır.
    Dönem başı bakiyelerini (devir) de dikkate almak daha kapsamlı bir çözüm gerektirir.
    Bu fonksiyon, belirtilen dönem içindeki *hareketleri* baz alarak bir tür "dönem mizanı" oluşturur.
    """
    try:
        yevmiye_baslik_ids_query = db.session.query(YevmiyeMaddesiBasligi.id)\
            .filter(
                YevmiyeMaddesiBasligi.firma_id == firma_id,
                # Yevmiye maddesinin muhasebe tarihi (postingDate) üzerinden filtreleme yapılmalı.
                # YevmiyeMaddesiBasligi.dosya_donemi_bitis yerine, satırların muhasebe_kayit_tarihi kullanılmalı.
            )
        
        # İlgili döneme ait tüm yevmiye satırlarını çek
        # Bu sorgu, yevmiye satırlarının muhasebe_kayit_tarihi'ne göre filtrelenmeli.
        # Ve bu satırların ait olduğu yevmiye başlıklarının da ilgili döneme ait olması sağlanmalı.
        # Örnek XML'de dosya_donemi_bitis var ama fişlerin kendi muhasebe tarihleri daha önemli.

        # Basitlik adına, dosya_donemi_bitis'i eşleşen tüm kayıtları alıyoruz.
        # Gerçek bir dönem analizi için bu sorgunun daha hassas olması gerekir.
        # Örneğin, tüm geçmiş hareketleri alıp kümülatif bakiye hesaplamak (Bilanço için)
        # veya sadece dönem içi hareketleri almak (Gelir Tablosu için).

        ilgili_maddeler_ids = db.session.query(YevmiyeMaddesiBasligi.id)\
            .filter(YevmiyeMaddesiBasligi.firma_id == firma_id,
                    YevmiyeMaddesiBasligi.dosya_donemi_bitis >= donem_baslangic_date, # Veya sadece donem_bitis_date'e eşit olanlar
                    YevmiyeMaddesiBasligi.dosya_donemi_bitis <= donem_bitis_date
                    )\
            .subquery()
            
        results = db.session.query(
            YevmiyeFisiSatiri.hesap_kodu,
            func.sum(YevmiyeFisiSatiri.borc_tutari).label('toplam_borc'),
            func.sum(YevmiyeFisiSatiri.alacak_tutari).label('toplam_alacak')
        ).join(YevmiyeMaddesiBasligi, YevmiyeFisiSatiri.yevmiye_maddesi_id == YevmiyeMaddesiBasligi.id)\
        .filter(
            YevmiyeMaddesiBasligi.firma_id == firma_id,
            YevmiyeFisiSatiri.muhasebe_kayit_tarihi >= donem_baslangic_date,
            YevmiyeFisiSatiri.muhasebe_kayit_tarihi <= donem_bitis_date
        ).group_by(
            YevmiyeFisiSatiri.hesap_kodu
        ).all()

        hesap_ozetleri = {}
        for row in results:
            hesap_kodu = row.hesap_kodu
            toplam_borc = float(row.toplam_borc or 0.0)
            toplam_alacak = float(row.toplam_alacak or 0.0)
            
            hesap_detayi = HESAP_DETAYLARI.get(hesap_kodu) # Ana hesap kodu ile eşleştirme
            if not hesap_detayi: # Ana hesap değilse veya map'te yoksa, ilk 3 hanesini almayı dene
                if len(hesap_kodu) > 3:
                    ana_hesap_kodu = hesap_kodu[:3]
                    hesap_detayi = HESAP_DETAYLARI.get(ana_hesap_kodu)
            
            net_bakiye = 0
            if hesap_detayi:
                if hesap_detayi['normal_balance'] == 'D': # Borç karakterli
                    net_bakiye = toplam_borc - toplam_alacak
                elif hesap_detayi['normal_balance'] == 'C': # Alacak karakterli
                    net_bakiye = toplam_alacak - toplam_borc
            else: # Bilinmeyen hesap karakteri, varsayılan olarak borç bakiyesi
                net_bakiye = toplam_borc - toplam_alacak
                
            hesap_ozetleri[hesap_kodu] = {
                'adi': hesap_detayi['adi'] if hesap_detayi else 'Bilinmeyen Hesap',
                'borc_hareket': toplam_borc,
                'alacak_hareket': toplam_alacak,
                'net_bakiye_veya_hareket': net_bakiye, # Bu, dönemsel hareket veya dönem sonu bakiye olabilir
                'normal_balance': hesap_detayi['normal_balance'] if hesap_detayi else 'D',
                'fs_impact': hesap_detayi['fs_impact'] if hesap_detayi else 1
            }
        logger.info(f"Firma {firma_id}, Dönem {donem_baslangic_date}-{donem_bitis_date} için hesap hareketleri özeti: {len(hesap_ozetleri)} hesap.")
        return hesap_ozetleri
    except Exception as e:
        logger.error(f"get_hesap_bakiyeleri_for_period hata: {e}", exc_info=True)
        raise # Hatanın yukarıya fırlatılması, route'da yakalanacak


def _recursive_map_hesaplar(hesap_bakiyeleri, tablo_yapi_grubu):
    """
    Verilen tablo yapısı ve hesap bakiyelerine göre mali tablo kalemlerini hesaplar.
    İç içe grupları da (şimdilik tek seviye) destekler.
    """
    grup_toplamlari = {}
    genel_toplam = 0
    for kalem_adi, hesap_kod_listesi_veya_altgrup in tablo_yapi_grubu.items():
        if isinstance(hesap_kod_listesi_veya_altgrup, list): # Doğrudan hesap kod listesi
            kalem_degeri = 0
            for kod in hesap_kod_listesi_veya_altgrup:
                if kod in hesap_bakiyeleri:
                    detay = HESAP_DETAYLARI.get(kod)
                    # Bilanço kalemleri için net bakiyeyi, gelir tablosu için dönemsel hareketi (net_bakiye_veya_hareket) kullan.
                    # fs_impact ile çarp.
                    if detay:
                         # Aktifler ve giderler için (normal_balance='D'), net_bakiye pozitifse fs_impact ile çarpılır.
                         # Pasifler ve gelirler için (normal_balance='C'), net_bakiye pozitifse fs_impact ile çarpılır.
                         # Düzenleyici hesaplar (örn: 257, 580, 610) kendi fs_impact'lerine göre etki eder.
                        kalem_degeri += hesap_bakiyeleri[kod]['net_bakiye_veya_hareket'] * detay.get('fs_impact', 1)
            grup_toplamlari[kalem_adi] = kalem_degeri
            genel_toplam += kalem_degeri
        elif isinstance(hesap_kod_listesi_veya_altgrup, dict): # Alt grup
            alt_grup_sonuclari, alt_grup_toplami_degeri = _recursive_map_hesaplar(hesap_bakiyeleri, hesap_kod_listesi_veya_altgrup)
            grup_toplamlari[kalem_adi] = alt_grup_sonuclari
            grup_toplamlari[kalem_adi]['TOPLAM'] = alt_grup_toplami_degeri
            genel_toplam += alt_grup_toplami_degeri
            
    return grup_toplamlari, genel_toplam


def generate_bilanco_from_ Bewegungen(hesap_bakiyeleri_donem_hareketleri):
    bilanco = {"AKTIFLER": {}, "PASIFLER": {}}
    
    # Bilanço hesapları için dönem sonu bakiyeleri gerekir.
    # Şu anki get_hesap_bakiyeleri_for_period fonksiyonu DÖNEM İÇİ HAREKETLERİ veriyor.
    # Gerçek bilanço için ya açılış bakiyeleri + dönem içi hareketler ya da direkt dönem sonu bakiyeleri gerekir.
    # Bu prototipte, hesap_bakiyeleri_donem_hareketleri'ndeki 'net_bakiye_veya_hareket' alanını
    # sanki dönem sonu bakiyesiymiş gibi kullanacağız (bu büyük bir basitleştirmedir).
    # TODO: Gerçek dönem sonu bakiye hesaplama mantığı eklenmeli.
    
    logger.info("Bilanço oluşturuluyor (basitleştirilmiş dönem sonu bakiye varsayımı ile)...")
    
    aktif_gruplari, aktif_toplami = _recursive_map_hesaplar(hesap_bakiyeleri_donem_hareketleri, BILANCO_YAPISI["AKTIFLER"])
    bilanco["AKTIFLER"] = aktif_gruplari
    bilanco["AKTIFLER"]["GENEL_TOPLAM"] = aktif_toplami

    pasif_gruplari, pasif_toplami = _recursive_map_hesaplar(hesap_bakiyeleri_donem_hareketleri, BILANCO_YAPISI["PASIFLER"])
    bilanco["PASIFLER"] = pasif_gruplari
    bilanco["PASIFLER"]["GENEL_TOPLAM"] = pasif_toplami
    
    logger.info(f"Bilanço oluşturuldu. Aktif Toplam: {aktif_toplami}, Pasif Toplam: {pasif_toplami}")
    if abs(aktif_toplami - pasif_toplami) > 0.01: # Küçük bir tolerans ile denklik kontrolü
        logger.warning(f"BİLANÇO DENKLİĞİ SAĞLANAMADI! Aktif: {aktif_toplami}, Pasif: {pasif_toplami}")
        bilanco["DENKLIK_SORUNU"] = f"Aktif ({aktif_toplami}) != Pasif ({pasif_toplami})"

    return bilanco


def generate_gelir_tablosu_from_hareketler(hesap_bakiyeleri_donem_hareketleri):
    gelir_tablosu_hesaplanmis = {}
    logger.info("Gelir tablosu oluşturuluyor...")

    for kalem_adi, hesap_kod_gruplari, etki_carpani, *hesaplama_fonk in GELIR_TABLOSU_YAPISI:
        if hesap_kod_gruplari: # Doğrudan hesaplardan toplanacaksa
            kalem_degeri = 0
            # Bu kısım _recursive_map_hesaplar gibi daha genel bir yapıya çekilebilir
            for grup_adi_veya_kod in hesap_kod_gruplari: # grup_adi_veya_kod aslında bir liste
                # grup_adi_veya_kod burada HESAP_PLANI_MAP içindeki anahtar olmalı
                # HESAP_PLANI_MAP['GELIR_TABLOSU'][grup_adi_veya_kod]
                # Bu yapı biraz daha düzeltilmeli. Şimdilik direkt kod listesi gibi varsayalım.
                # Veya HESAP_DETAYLARI'ndaki 'grup' ve 'fs_kalem' alanlarını kullanalım.
                
                # Basitleştirilmiş:
                for kod in HESAP_PLANI_MAP['GELIR_TABLOSU'].get(grup_adi_veya_kod, []): # Eğer grup_adi_veya_kod bir grup adıysa
                    if kod in hesap_bakiyeleri_donem_hareketleri:
                        detay = HESAP_DETAYLARI.get(kod)
                        if detay:
                             # Gelir tablosu hesapları için 'net_bakiye_veya_hareket' zaten dönemsel hareketi gösterir.
                             # fs_impact burada önemli. Gelirler pozitif, giderler/indirimler negatif etki eder.
                            kalem_degeri += hesap_bakiyeleri_donem_hareketleri[kod]['net_bakiye_veya_hareket'] * detay.get('fs_impact', 1)

            # Gelir tablosunda giderler ve indirimler genellikle pozitif raporlanır ama toplamdan düşülür.
            # Bizim fs_impact zaten bunu yapıyor olmalı. etki_carpani'nı bu durumda fs_impact'e bırakabiliriz.
            # Ancak GELIR_TABLOSU_YAPISI'ndaki etki_carpani, kalemin genel toplama etkisini belirtir.
            gelir_tablosu_hesaplanmis[kalem_adi] = kalem_degeri # etki_carpani'nı sonra uygula
        
        elif hesaplama_fonk: # Ara toplam veya hesaplama fonksiyonu varsa
            gelir_tablosu_hesaplanmis[kalem_adi] = hesaplama_fonk[0](gelir_tablosu_hesaplanmis)
    
    # Netleştirmek için: Gider ve indirimler pozitif değerler olarak hesaplandıysa, ana toplamlardan çıkarılacaklar.
    # GELIR_TABLOSU_YAPISI'ndaki etki_carpani'nı kullanarak sonuçları ayarlayalım.
    # Bu örnekte, _calculate_kalem_toplami zaten fs_impact'i kullandığı için,
    # GELIR_TABLOSU_YAPISI'ndaki etki_carpani, o kalemin genel toplama işaretini belirtebilir.
    # Şu anki yapıda _calculate_kalem_toplami ve HESAP_DETAYLARI['fs_impact'] ana mantığı taşıyor.
    # GELIR_TABLOSU_YAPISI'ndaki hesaplama fonksiyonları daha doğru bir yaklaşım.

    # Örnekteki lambda fonksiyonlarını kullanarak ara toplamları hesaplayalım.
    # Bu, GELIR_TABLOSU_YAPISI'nın doğru işlenmesini gerektirir.
    # Bu kısım daha robust bir şekilde, yapıya göre iteratif hesaplama yapmalı.
    # Geçici olarak bazı anahtar kalemleri manuel hesaplayalım (yapıdaki lambdalara göre):
    if 'NET SATIŞLAR' not in gelir_tablosu_hesaplanmis and callable(GELIR_TABLOSU_YAPISI[2][3]):
         gelir_tablosu_hesaplanmis['NET SATIŞLAR'] = GELIR_TABLOSU_YAPISI[2][3](gelir_tablosu_hesaplanmis)
    if 'BRÜT SATIŞ KÂRI (ZARARI)' not in gelir_tablosu_hesaplanmis and callable(GELIR_TABLOSU_YAPISI[4][3]):
         gelir_tablosu_hesaplanmis['BRÜT SATIŞ KÂRI (ZARARI)'] = GELIR_TABLOSU_YAPISI[4][3](gelir_tablosu_hesaplanmis)
    # ... diğer ara toplamlar ...

    logger.info(f"Gelir Tablosu (basitleştirilmiş) oluşturuldu: {gelir_tablosu_hesaplanmis.get('NET SATIŞLAR')}")
    return gelir_tablosu_hesaplanmis