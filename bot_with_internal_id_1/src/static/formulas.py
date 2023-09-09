round_arg = 3


def formula_for_total_volume_calculation_before_30_days(sum_arg: int | float) -> float:
    return float(round(sum_arg * 100 / 40, round_arg))


def formula_for_total_volume_calculation_after_30_days(sum_arg: int | float) -> float:
    return float(round(sum_arg * 100 / 30, round_arg))


def level1_futures_less30(sum_arg: int | float) -> float:
    return float(round(((sum_arg * 100 / 40) * 25) / 100, round_arg))


def level1_futures_more30(sum_arg: int | float) -> float:
    return float(round(((sum_arg * 100 / 30) * 25) / 100, round_arg))


def level1_spot_less30(sum_arg: int | float) -> float:
    return float(round(((sum_arg * 100 / 41) * 30) / 100, round_arg))


def level1_spot_more30(sum_arg: int | float) -> float:
    return float(round(((sum_arg * 100 / 41) * 30) / 100, round_arg))


def level1_bnb_less30(sum_arg: int | float) -> float:
    return float(((sum_arg * 100 / 41) * 30) / 100)


def level1_bnb_more30(sum_arg: int | float) -> float:
    return float(((sum_arg * 100 / 41) * 30) / 100)


def level2_futures_less30(sum_arg: int | float) -> float:
    return float(round(sum_arg, round_arg))


def level2_futures_more30(sum_arg: int | float) -> float:
    return float(round(sum_arg, round_arg))


def level2_spot_less30(sum_arg: int | float) -> float:
    return float(round(sum_arg, round_arg))


def level2_spot_more30(sum_arg: int | float) -> float:
    return float(round(sum_arg, round_arg))


def level2_bnb_less30(sum_arg: int | float) -> float:
    return float(round(sum_arg, round_arg))


def level2_bnb_more30(sum_arg: int | float) -> float:
    return float(round(sum_arg, round_arg))
