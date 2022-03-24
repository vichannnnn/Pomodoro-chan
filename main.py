from abc import ABC
import lightbulb
import yaml
import hikari
from os import listdir
from os.path import abspath
import miru
from lightbulb.ext import tasks

with open("authentication.yaml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)

intents = hikari.Intents.ALL

class Yuna(lightbulb.BotApp, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_configuration(self):
        self.load_all_extensions()

    def load_all_extensions(self):
        for file in listdir(abspath("components/")):
            if file.endswith(".py"):
                f = file
                file = "components." + file[:-3]
                self.load_extensions(file)
                print(f"Successfully loaded {f[:-3]}")

    def load_tasks(self):
        tasks.load(self)


def main():
    instance = Yuna(token=yaml_data['Token'], prefix=lightbulb.when_mentioned_or(None),
                    default_enabled_guilds=[], intents=intents, help_class=None, owner_ids=yaml_data['Owners'])
    miru.load(instance)

    @instance.listen()
    async def on_ready(event: hikari.StartedEvent) -> None:
        guilds = instance.rest.fetch_my_guilds()
        print(f"{instance.get_me().username} ({instance.get_me().id}) successfully started.")
        print(f"Currently in {await guilds.count()} guilds.")

    instance.load_tasks()
    instance.load_configuration()
    instance.run()


main()
