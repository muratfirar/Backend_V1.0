# app/services.py

def calculate_cari_oran(donen_varliklar, kisa_vadeli_yukumlulukler):
    if kisa_vadeli_yukumlulukler is None or kisa_vadeli_yukumlulukler == 0:
        return None
    if donen_varliklar is None:
        return None
    try:
        return round(float(donen_varliklar) / float(kisa_vadeli_yukumlulukler), 4)
    except (TypeError, ValueError):
        return None

def calculate_borc_ozkaynak_orani(toplam_yukumlulukler, oz_kaynaklar):
    if oz_kaynaklar is None or oz_kaynaklar == 0:
        return None
    if toplam_yukumlulukler is None:
        return None
    try:
        return round(float(toplam_yukumlulukler) / float(oz_kaynaklar), 4)
    except (TypeError, ValueError):
        return None

def calculate_altman_z_score_updated(
    donen_varliklar, aktif_toplami, kisa_vadeli_yukumlulukler,
    dagitilmamis_karlar, vergi_oncesi_kar_zarar, oz_kaynaklar,
    toplam_yukumlulukler, net_satislar
    ):
    try:
        donen_varliklar = float(donen_varliklar)
        aktif_toplami = float(aktif_toplami)
        kisa_vadeli_yukumlulukler = float(kisa_vadeli_yukumlulukler)
        dagitilmamis_karlar = float(dagitilmamis_karlar)
        vergi_oncesi_kar_zarar = float(vergi_oncesi_kar_zarar)
        oz_kaynaklar = float(oz_kaynaklar)
        toplam_yukumlulukler = float(toplam_yukumlulukler)
        net_satislar = float(net_satislar)
    except (TypeError, ValueError, AttributeError):
        return None

    if aktif_toplami == 0 or toplam_yukumlulukler == 0 or oz_kaynaklar == 0:
        return None

    net_isletme_sermayesi = donen_varliklar - kisa_vadeli_yukumlulukler
    x1 = net_isletme_sermayesi / aktif_toplami
    x2 = dagitilmamis_karlar / aktif_toplami
    x3 = vergi_oncesi_kar_zarar / aktif_toplami 
    x4 = oz_kaynaklar / toplam_yukumlulukler 
    x5 = net_satislar / aktif_toplami
    
    z_score = (0.717 * x1) + (0.847 * x2) + (3.107 * x3) + (0.420 * x4) + (0.998 * x5)
    return round(z_score, 4)