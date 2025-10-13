from pydantic import BaseModel


class PrivateChatCreate(BaseModel):
    user2_id: int


class ChatResponse(BaseModel):
    chat_id: int
    message: str
