from pydantic import BaseModel

class AttachmentOut(BaseModel):
    id: int
    file_url: str
    file_type: str | None = None
    file_size: int | None = None

    model_config = {
        "from_attributes": True
    }