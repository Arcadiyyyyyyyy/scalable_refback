from fastapi import APIRouter
from .calculations import calculate_sum_for_users
from .db import prune_cached_csv

router = APIRouter(prefix="/calculations", tags=["Image"])


@router.get("/get_calculation_results_for_all_users/{}")
async def get_calculation_results_for_all_users(bot_internal_id: int):
    return calculate_sum_for_users(bot_internal_id)


@router.post("/prune_db_documents_with_internal_id/{}")
async def prune_db_documents_with_internal_id(bot_internal_id: int):
    if prune_cached_csv(bot_internal_id).deleted_count > 0:
        return "Success"
    else:
        return "Nothing was deleted, perhaps there is nothing to prune"
