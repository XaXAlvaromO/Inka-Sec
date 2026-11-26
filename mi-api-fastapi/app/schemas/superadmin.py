from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import EMAIL_PATTERN


class CompanyCreate(BaseModel):
    """Alta de una empresa nueva junto con su primer administrador.

    El nombre de la empresa es lo que la distingue de las demás en el panel del
    superadministrador (HU pedida por Vero); el correo del administrador no puede
    repetirse con el de ningún usuario de ninguna empresa.
    """

    model_config = ConfigDict(str_strip_whitespace=True)
    company_name: str = Field(min_length=2, max_length=120)
    admin_name: str = Field(min_length=2, max_length=120)
    admin_email: str = Field(min_length=5, max_length=180, pattern=EMAIL_PATTERN)
