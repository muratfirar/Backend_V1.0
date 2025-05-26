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