from enum import Enum


class LanguageCodes(Enum):
    english = "en"
    russian = "ru"
    ukrainian = "ua"


class QueryCategories(Enum):
    commands = "c"
    conversation_handlers = "ch"
    support = "sp"
    admin = "adm"
    new_ticket = "new"


class QueryCommands(Enum):
    lang_code_handle = "l_c_h"
    confirm_handle = "con_h"
    delete = "d"
    delete_message = "dlt_m"
    menu = "menu"
    support = "support"
    new_ticket = "n_t"
    my_open_tickets = "my_o_t"
    support_help = "sp_hp"
    admin = "admin"
    ticket = "ticket"
    ticket_select = "t_sel"
    ticket_close = "t_cls"
    skip = "skip"
    get_link_to_filechanger_or_document = "gltfd"
    current_withdraw_list = "cwd"
    notify_new_payoff = "nnp"
    increase_level = "il"
    decrease_level = "dl"


class AdminLevels(Enum):
    any_admin = 1
    support_level = 3
    owner_level = 10


class CommandsRelated(Enum):
    command_name = "command_name"
    command_description = "command_description"


class CommandsWithDescriptions(Enum):
    # menu = {
    #     CommandsRelated.command_name.value: "menu",
    #     CommandsRelated.command_description.value: "Command Description (currently placeholder)"  # TODO: get actual
    # }
    my_data = {
        CommandsRelated.command_name.value: "my_data",
        CommandsRelated.command_description.value: "Ваши данные 👀"
    }
    set_data = {
        CommandsRelated.command_name.value: "set_data",
        CommandsRelated.command_description.value: "Зарегистрироваться ✍️"
    }
    # help = {
    #     CommandsRelated.command_name.value: "help",
    #     CommandsRelated.command_description.value: "Помощь по командам"
    # }
    support = {
        CommandsRelated.command_name.value: "support",
        CommandsRelated.command_description.value: "Всё связанное с поддержкой"
    }
    exit = {
        CommandsRelated.command_name.value: "exit",
        CommandsRelated.command_description.value: "Выйти из активного тикета поддержки"
    }
    cancel = {
        CommandsRelated.command_name.value: "cancel",
        CommandsRelated.command_description.value: "Отменить команду"
    }
    start = {
        CommandsRelated.command_name.value: "start",
        CommandsRelated.command_description.value: "Помощь по командам"
    }


class MinimumWithdrawValues(Enum):
    usdt = 1
    bnb = 0.01


class WithdrawCommissions(Enum):
    usdt_commission = 4.0
    bnb_commission = 0.005


class FilechangerLinkRegex(Enum):
    pixel_drain = r"https://pixeldrain.com/u/[a-zA-Z0-9]{3-12}"


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


class Other(Enum):
    bot_id = 1
    manual_support = "@cheeeryyygirs"
    maximum_user_level = 2
