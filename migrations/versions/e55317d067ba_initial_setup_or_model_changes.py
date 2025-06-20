"""initial_setup_or_model_changes

Revision ID: e55317d067ba
Revises: 0af3b0f13311
Create Date: 2025-05-12 00:53:10.181723

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e55317d067ba'
down_revision = '0af3b0f13311'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('finansal_veri', schema=None) as batch_op:
        batch_op.add_column(sa.Column('donen_varliklar', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('duran_varliklar', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('kisa_vadeli_yukumlulukler', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('uzun_vadeli_yukumlulukler', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('toplam_yukumlulukler', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('oz_kaynaklar', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('net_satislar', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('satilan_malin_maliyeti', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('brut_kar_zarar', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('faaliyet_giderleri', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('esas_faaliyet_kari_zarari', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('finansman_giderleri', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('vergi_oncesi_kar_zarar', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('donem_net_kari_zarari', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('cari_oran', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('borc_ozkaynak_orani', sa.Float(), nullable=True))
        batch_op.alter_column('donem',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.String(length=50),
               nullable=False)
        batch_op.create_unique_constraint('_firma_donem_uc', ['firma_id', 'donem'])
        batch_op.drop_column('yillik_satislar')
        batch_op.drop_column('toplam_borclar')
        batch_op.drop_column('kisa_vadeli_borclar')
        batch_op.drop_column('oz_sermaye_piyasa_degeri')
        batch_op.drop_column('faiz_vergi_oncesi_kar')

    with op.batch_alter_table('firma', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('firma', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    with op.batch_alter_table('finansal_veri', schema=None) as batch_op:
        batch_op.add_column(sa.Column('faiz_vergi_oncesi_kar', sa.FLOAT(), nullable=True))
        batch_op.add_column(sa.Column('oz_sermaye_piyasa_degeri', sa.FLOAT(), nullable=True))
        batch_op.add_column(sa.Column('kisa_vadeli_borclar', sa.FLOAT(), nullable=True))
        batch_op.add_column(sa.Column('toplam_borclar', sa.FLOAT(), nullable=True))
        batch_op.add_column(sa.Column('yillik_satislar', sa.FLOAT(), nullable=True))
        batch_op.drop_constraint('_firma_donem_uc', type_='unique')
        batch_op.alter_column('donem',
               existing_type=sa.String(length=50),
               type_=sa.VARCHAR(length=20),
               nullable=True)
        batch_op.drop_column('borc_ozkaynak_orani')
        batch_op.drop_column('cari_oran')
        batch_op.drop_column('donem_net_kari_zarari')
        batch_op.drop_column('vergi_oncesi_kar_zarar')
        batch_op.drop_column('finansman_giderleri')
        batch_op.drop_column('esas_faaliyet_kari_zarari')
        batch_op.drop_column('faaliyet_giderleri')
        batch_op.drop_column('brut_kar_zarar')
        batch_op.drop_column('satilan_malin_maliyeti')
        batch_op.drop_column('net_satislar')
        batch_op.drop_column('oz_kaynaklar')
        batch_op.drop_column('toplam_yukumlulukler')
        batch_op.drop_column('uzun_vadeli_yukumlulukler')
        batch_op.drop_column('kisa_vadeli_yukumlulukler')
        batch_op.drop_column('duran_varliklar')
        batch_op.drop_column('donen_varliklar')

    # ### end Alembic commands ###
