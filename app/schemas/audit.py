"""Aile audit — kayıtların yanında "kim ekledi" bilgisini taşımak için.

Bir kullanıcının bebekle olan ilişkisi (anne / baba / bakıcı...) bebek
bazlıdır, bu yüzden ActorOut.relationship bağlam içinde bebek için doldurulur.
"""

from pydantic import BaseModel

from app.models.baby_member import BabyRelationship


class ActorOut(BaseModel):
    """Bir kaydı oluşturan kullanıcının özet bilgisi.

    `relationship` ve `relationship_label` çağrılan endpoint'in bebek
    bağlamında ek doldurulur. user silindiyse (created_by_user_id NULL)
    None döndürmek tercih edilir.
    """

    id: int
    name: str
    relationship: BabyRelationship | None = None
    relationship_label: str | None = None
