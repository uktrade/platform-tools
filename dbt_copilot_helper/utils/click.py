from click import Argument
from click import Choice
from click import Command
from click import Context
from click import Group
from click import HelpFormatter


class ClickDocOptCommand(Command):
    def format_usage(self, ctx: Context, formatter: HelpFormatter) -> None:
        format_click_usage(ctx, formatter)


class ClickDocOptGroup(Group):
    command_class = ClickDocOptCommand

    def format_usage(self, ctx: Context, formatter: HelpFormatter) -> None:
        format_click_usage(ctx, formatter, True)


def format_click_usage(ctx: Context, formatter: HelpFormatter, group: bool = False) -> None:
    help_text = f"Usage: {ctx.command_path} "
    current_line = 0
    indent = len(help_text)

    parameters = list(ctx.command.params)
    parameters.sort(key=lambda p: p.required, reverse=True)
    parameters.sort(key=lambda p: hasattr(p, "is_flag") and p.is_flag)
    parameters.sort(key=lambda p: p.__class__.__name__ == "Option")

    if group:
        command_list = list(ctx.command.commands.keys())

        if len(command_list) == 1:
            help_text += f"{command_list[0]} "
        elif len(command_list) <= 4:
            parameters.insert(0, Argument(["command"], type=Choice(command_list)))
        else:
            parameters.insert(0, Argument(["command"]))

    for index, param in enumerate(parameters):
        if param.__class__.__name__ == "Argument":
            if hasattr(param.type, "choices"):
                wrap = "(%s) " if param.required else "[(%s)] "
                help_text += wrap % "|".join(param.type.choices)
            else:
                wrap = "<%s> " if param.required else "[<%s>] "
                help_text += wrap % param.name
        elif param.__class__.__name__ == "Option":
            if (
                parameters[index - 1].__class__.__name__ == "Argument"
                and not help_text.split("\n")[current_line].isspace()
                and len(help_text.split("\n")[current_line]) > 40
            ):
                help_text += "\n" + (" " * indent)
                current_line += 1
            if getattr(param, "is_flag", False):
                wrap = "%s " if param.required else "[%s] "
                options = param.opts
                if getattr(param, "default", None) is None:
                    options += param.secondary_opts
                help_text += wrap % "|".join(options)
            elif hasattr(param.type, "choices"):
                wrap = "%s (%s) " if param.required else "[%s (%s)] "
                help_text += wrap % (param.opts[0], "|".join(param.type.choices))
            else:
                wrap = "%s <%s> " if param.required else "[%s <%s>] "
                help_text += wrap % (param.opts[0], param.name)

        if index + 1 != len(parameters) and len(help_text.split("\n")[current_line]) > 70:
            help_text += "\n" + (" " * indent)
            current_line += 1

    formatter.write(f"{help_text}\n")
