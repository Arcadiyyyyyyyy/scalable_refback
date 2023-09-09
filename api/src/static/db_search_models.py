from enum import Enum


class OrderType(Enum):
    usdt_futures = "USDT-futures"
    spot = "spot"


class CommissionAsset(Enum):
    bnb = "BNB"
    usdt = "USDT"
    busd = "BUSD"


class CsvColumns(Enum):
    order_type = "Order Type"
    friend_id_spot = "Friend's ID(Spot)"
    friend_id_sub_spot = "Friend's sub ID (Spot)"
    commission_asset = "Commission Asset"
    coin_commission_earned = "Commission Earned"
    usdt_commission_earned = "Commission Earned (USDT)"
    commission_time = "Commission Time"
    registration_time = "Registration Time"
    referral_id = "Referral ID"
