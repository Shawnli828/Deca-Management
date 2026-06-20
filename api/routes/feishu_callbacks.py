from fastapi import APIRouter, Request

from server_modules.services.feishu_callback_service import handle_card_action


router = APIRouter()


@router.post("/api/feishu/card-actions")
async def post_feishu_card_actions(request: Request):
    payload = await request.json()
    return handle_card_action(payload)
