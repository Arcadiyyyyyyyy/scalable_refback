from .db import aggregate_cached_csv, read_all_used_buids_in_cached_csv
from .static.db_search_models import CommissionAsset, OrderType


def calculate_sum_for_users(bot_internal_id: int):
    data = {
        int(x): {
            "sum_results_before_user_used_the_bot_for_30_days": {
                "spot": {},
                "futures": {}
            },
            "sum_results_after_user_used_the_bot_for_30_days": {
                "spot": {},
                "futures": {}
            }
        } for x in read_all_used_buids_in_cached_csv()
    }

    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.spot.value,
        CommissionAsset.usdt.value,
        "lt"
    ):
        data[
            x.get("_id")
        ]["sum_results_before_user_used_the_bot_for_30_days"]["spot"]["usdt"] = x.get("USDT_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.spot.value,
        CommissionAsset.busd.value,
        "lt"
    ):
        data[
            x.get("_id")
        ]["sum_results_before_user_used_the_bot_for_30_days"]["spot"]["busd"] = x.get("COIN_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.spot.value,
        CommissionAsset.bnb.value,
        "lt"
    ):
        data[
            x.get("_id")
        ]["sum_results_after_user_used_the_bot_for_30_days"]["spot"]["bnb"] = x.get("COIN_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.spot.value,
        CommissionAsset.usdt.value,
        "gte"
    ):
        data[
            x.get("_id")
        ]["sum_results_after_user_used_the_bot_for_30_days"]["spot"]["usdt"] = x.get("USDT_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.spot.value,
        CommissionAsset.busd.value,
        "gte"
    ):
        data[
            x.get("_id")
        ]["sum_results_after_user_used_the_bot_for_30_days"]["spot"]["busd"] = x.get("COIN_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.spot.value,
        CommissionAsset.bnb.value,
        "gte"
    ):
        data[
            x.get("_id")
        ]["sum_results_after_user_used_the_bot_for_30_days"]["spot"]["bnb"] = x.get("COIN_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.usdt_futures.value,
        CommissionAsset.usdt.value,
        "lt"
    ):
        data[
            x.get("_id")
        ]["sum_results_before_user_used_the_bot_for_30_days"]["futures"]["usdt"] = x.get("USDT_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.usdt_futures.value,
        CommissionAsset.busd.value,
        "lt"
    ):
        data[
            x.get("_id")
        ]["sum_results_before_user_used_the_bot_for_30_days"]["futures"]["busd"] = x.get("COIN_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.usdt_futures.value,
        CommissionAsset.bnb.value,
        "lt"
    ):
        data[
            x.get("_id")
        ]["sum_results_before_user_used_the_bot_for_30_days"]["futures"]["bnb"] = x.get("COIN_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.usdt_futures.value,
        CommissionAsset.usdt.value,
        "gte"
    ):
        data[
            x.get("_id")
        ]["sum_results_after_user_used_the_bot_for_30_days"]["futures"]["usdt"] = x.get("USDT_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.usdt_futures.value,
        CommissionAsset.busd.value,
        "gte"
    ):
        data[
            x.get("_id")
        ]["sum_results_after_user_used_the_bot_for_30_days"]["futures"]["busd"] = x.get("COIN_COMMISSION_SUM")
    for x in aggregate_cached_csv(
        bot_internal_id,
        OrderType.usdt_futures.value,
        CommissionAsset.bnb.value,
        "gte"
    ):
        data[
            x.get("_id")
        ]["sum_results_after_user_used_the_bot_for_30_days"]["futures"]["bnb"] = x.get("COIN_COMMISSION_SUM")

    return data
