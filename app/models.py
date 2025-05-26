from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Firma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    adi = db.Column(db.String(120), nullable=False, index=True)
    vkn = db.Column(db.String(20), unique=True, nullable=False) # nullable=False olarak güncellendi
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    sahibi = db.relationship('User', backref=db.backref('firmalar', lazy='dynamic'))
    finansal_veriler = db.relationship('FinansalVeri', backref='firma_ref', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Firma {self.adi}>'

class FinansalVeri(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('firma.id'), nullable=False)
    donem = db.Column(db.String(50), nullable=False)

    donen_varliklar = db.Column(db.Float, default=0.0)
    duran_varliklar = db.Column(db.Float, default=0.0)
    aktif_toplami = db.Column(db.Float, default=0.0)
    kisa_vadeli_yukumlulukler = db.Column(db.Float, default=0.0)
    uzun_vadeli_yukumlulukler = db.Column(db.Float, default=0.0)
    toplam_yukumlulukler = db.Column(db.Float, default=0.0)
    oz_kaynaklar = db.Column(db.Float, default=0.0)
    net_satislar = db.Column(db.Float, default=0.0)
    satilan_malin_maliyeti = db.Column(db.Float, default=0.0)
    brut_kar_zarar = db.Column(db.Float, default=0.0)
    faaliyet_giderleri = db.Column(db.Float, default=0.0)
    esas_faaliyet_kari_zarari = db.Column(db.Float, default=0.0)
    finansman_giderleri = db.Column(db.Float, default=0.0)
    vergi_oncesi_kar_zarar = db.Column(db.Float, default=0.0)
    donem_net_kari_zarari = db.Column(db.Float, default=0.0)
    dagitilmamis_karlar = db.Column(db.Float, default=0.0)
    
    cari_oran = db.Column(db.Float, nullable=True)
    borc_ozkaynak_orani = db.Column(db.Float, nullable=True)
    altman_z_skoru = db.Column(db.Float, nullable=True)

    __table_args__ = (db.UniqueConstraint('firma_id', 'donem', name='_firma_donem_uc'),)

    def __repr__(self):
        return f'<FinansalVeri FirmaID: {self.firma_id} Dönem: {self.donem}>'
        
# app/models.py dosyasının sonuna eklenecek yeni modeller

class YevmiyeMaddesiBasligi(db.Model): # <gl-cor:entryHeader> karşılığı
    __tablename__ = 'yevmiye_maddesi_basligi'
    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('firma.id'), nullable=False, index=True)
    
    # E-Defter dosyasının genel bilgilerinden (documentInfo)
    dosya_donemi_baslangic = db.Column(db.Date) # <gl-cor:periodCoveredStart>
    dosya_donemi_bitis = db.Column(db.Date, index=True)     # <gl-cor:periodCoveredEnd> (Filtreleme için önemli)
    orjinal_dosya_adi = db.Column(db.String(255), nullable=True)
    yuklenme_tarihi = db.Column(db.DateTime, default=db.func.current_timestamp())

    # <gl-cor:entryHeader> elemanlarından
    yevmiye_madde_no_counter = db.Column(db.String(50), index=True) # <gl-cor:entryNumberCounter> [cite: 22, 49]
    muhasebe_fis_no = db.Column(db.String(100), nullable=True, index=True) # <gl-cor:entryNumber> (Kayıt Tanıtıcısı) [cite: 22, 33]
    kayit_tarihi_giris = db.Column(db.Date, nullable=True) # <gl-cor:enteredDate> (Fişin sisteme kayıt tarihi) [cite: 22, 31]
    aciklama_baslik = db.Column(db.Text, nullable=True)     # <gl-cor:entryComment> [cite: 22, 35]
    toplam_borc = db.Column(db.Numeric(18, 2))       # <gl-bus:totalDebit> [cite: 22, 43]
    toplam_alacak = db.Column(db.Numeric(18, 2))     # <gl-bus:totalCredit> [cite: 22, 45]
    
    # İlişki: Bir yevmiye maddesinin birden çok satırı olabilir
    satirlar = db.relationship('YevmiyeFisiSatiri', backref='yevmiye_maddesi', lazy='select', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<YevmiyeMaddesiBasligi ID: {self.id}, FirmaID: {self.firma_id}, MaddeNo: {self.yevmiye_madde_no_counter}>'


class YevmiyeFisiSatiri(db.Model): # <gl-cor:entryDetail> karşılığı
    __tablename__ = 'yevmiye_fisi_satiri'
    id = db.Column(db.Integer, primary_key=True)
    yevmiye_maddesi_id = db.Column(db.Integer, db.ForeignKey('yevmiye_maddesi_basligi.id'), nullable=False, index=True)
    
    # <gl-cor:entryDetail> elemanlarından
    muhasebe_kayit_tarihi = db.Column(db.Date, nullable=False, index=True) # <gl-cor:postingDate> (Asıl yevmiye tarihi) [cite: 24, 95]
    hesap_kodu = db.Column(db.String(50), nullable=False, index=True)    # <gl-cor:accountMainID> [cite: 24, 65]
    hesap_adi = db.Column(db.String(255), nullable=True)                # <gl-cor:accountMainDescription> [cite: 24, 67]
    alt_hesap_kodu = db.Column(db.String(50), nullable=True, index=True) # <gl-cor:accountSubID> [cite: 24, 74]
    alt_hesap_adi = db.Column(db.String(255), nullable=True)            # <gl-cor:accountSubDescription> [cite: 24, 72]
    
    borc_tutari = db.Column(db.Numeric(18, 2), default=0.0)             # <gl-cor:amount> (debitCreditCode 'D' ise) [cite: 24, 76, 93]
    alacak_tutari = db.Column(db.Numeric(18, 2), default=0.0)           # <gl-cor:amount> (debitCreditCode 'C' ise) [cite: 24, 76, 93]
    
    aciklama_satir = db.Column(db.Text, nullable=True)                  # <gl-cor:detailComment> [cite: 24, 112]
    belge_tipi = db.Column(db.String(50), nullable=True)                # <gl-cor:documentType> [cite: 24, 97]
    belge_tipi_aciklama = db.Column(db.String(255), nullable=True)     # <gl-cor:documentTypeDescription> [cite: 24, 99] (eğer documentType 'other' ise)
    belge_no = db.Column(db.String(100), nullable=True, index=True)     # <gl-cor:documentNumber> [cite: 24, 101]
    belge_tarihi = db.Column(db.Date, nullable=True, index=True)        # <gl-cor:documentDate> [cite: 24, 107]
    belge_referansi = db.Column(db.String(100), nullable=True)          # <gl-cor:documentReference> [cite: 24, 105] (Genellikle yevmiye madde fiş no)
    odeme_yontemi = db.Column(db.String(100), nullable=True)            # <gl-bus:paymentMethod> [cite: 24, 109]
    
    # Yevmiye Defteri Kılavuzu'ndaki lineNumber ve lineNumberCounter da eklenebilir,
    # ancak bunlar daha çok XML içindeki sıralama ve referans için, DB'de id yeterli olabilir.
    # Yine de denetim için eklemek isteyebilirsiniz:
    # yevmiye_defteri_satir_no = db.Column(db.String(50)) # <gl-cor:lineNumber>
    # yevmiye_madde_ref_no_counter = db.Column(db.String(50)) # <gl-cor:lineNumberCounter> (parent'ın yevmiye_madde_no_counter'ı)


    def __repr__(self):
        return f'<YevmiyeFisiSatiri ID: {self.id}, MaddeID: {self.yevmiye_maddesi_id}, Hesap: {self.hesap_kodu}, Borç: {self.borc_tutari}, Alacak: {self.alacak_tutari}>'