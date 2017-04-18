from pyplanet.apps.config import AppConfig
from pyplanet.core.events import receiver

from pyplanet.apps.core.trackmania import callbacks as tm_signals
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals
from pyplanet.utils import times

from .models import LocalRecord

class LocalRecordsConfig(AppConfig):
	name = 'pyplanet.apps.contrib.local_records'
	game_dependencies = ['trackmania']
	app_dependencies = ['core.maniaplanet', 'core.trackmania']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.current_records = []

	async def on_ready(self):
		self.map_begin()
		self.player_finish()

		record_list = await LocalRecord.objects.execute(LocalRecord.select().where(LocalRecord.map_id == self.instance.map_manager.current_map.get_id()).order_by(LocalRecord.score.asc()))
		self.current_records = list(record_list)
		await self.chat_current_record()

	@receiver(mp_signals.map.map_begin)
	async def map_begin(self, map):
		record_list = await LocalRecord.objects.execute(LocalRecord.select().where(LocalRecord.map_id == map.get_id()).order_by(LocalRecord.score.asc()))
		self.current_records = list(record_list)
		await self.chat_current_record()

	@receiver(tm_signals.finish)
	async def player_finish(self, player, race_time, lap_time, cps, flow, raw, **kwargs):
		current_records = [x for x in self.current_records if x.player_id == player.get_id()]
		if len(current_records) > 0:
			current_record = current_records[0]
			previous_index = self.current_records.index(current_record) + 1

			if race_time < current_record.score:
				previous_time = current_record.score

				current_record.score = race_time
				current_record.checkpoints = ','.join(str(cp) for cp in cps)
				await current_record.save()

				self.current_records.append(current_record)
				self.current_records.sort(key=lambda x: x.score)

				new_index = self.current_records.index(current_record) + 1

				if new_index < previous_index:
					message = '$z$s> $fff{}$z$s$0f3 gained the $fff{}.$0f3 Local Record, with a time of $fff{}$0f3 ($fff{}.$0f3 $fff-{}$0f3).'.format(
						player.nickname, new_index, times.format_time(race_time), previous_index, times.format_time((previous_time - race_time))
					)
				else:
					message = '$z$s> $fff{}$z$s$0f3 improved the $fff{}.$0f3 Local Record, with a time of $fff{}$0f3 ($fff-{}$0f3).'.format(
						player.nickname, new_index, times.format_time(race_time), times.format_time((previous_time - race_time))
					)

				await self.instance.gbx.execute('ChatSendServerMessage', message)

			elif race_time == current_record.score:
				message = '$z$s> $fff{}$z$s$0f3 equalled the $fff{}.$0f3 Local Record, with a time of $fff{}$0f3.'.format(
					player.nickname, previous_index, times.format_time(race_time)
				)
				await self.instance.gbx.execute('ChatSendServerMessage', message)

		else:
			new_record = LocalRecord(map=self.instance.map_manager.current_map, player=player, score=race_time, cps=','.join(str(cp) for cp in cps))
			await new_record.save()

			self.current_records.append(new_record)
			self.current_records.sort(key=lambda x: x.score)
			new_index = self.current_records.index(new_record) + 1

			message = '$z$s> $fff{}$z$s$0f3 drove the $fff{}.$0f3 Local Record, with a time of $fff{}$0f3.'.format(
				player.nickname, new_index, times.format_time(race_time)
			)
			await self.instance.gbx.execute('ChatSendServerMessage', message)

	async def chat_current_record(self):
		records_amount = len(self.current_records)
		if records_amount > 0:
			first_record = self.current_records[0]
			message = '$z$s> $0f3Current Local Record: $fff{}$z$s$0f3 by $fff{}$z$s$0f3 (records: $fff{}$0f3)'.format(
				times.format_time(first_record.score), (await first_record.player).nickname, records_amount
			)
			await self.instance.gbx.execute('ChatSendServerMessage', message)

			for player in self.instance.player_manager.online:
				await self.chat_personal_record(player)
		else:
			message = '$z$s> $0f3There is no Local Record on this map yet.'
			await self.instance.gbx.execute('ChatSendServerMessage', message)

	async def chat_personal_record(self, player):
		record = [x for x in self.current_records if x.player_id == player.get_id()]

		if len(record) > 0:
			message = '$z$s> $0f3You currently hold the $fff{}.$0f3 Local Record: $fff{}'.format(
				self.current_records.index(record[0]) + 1, times.format_time(record[0].score)
			)
			await self.instance.gbx.execute('ChatSendServerMessageToLogin', message, player.login)
		else:
			message = '$z$s> $0f3You don\'t have a Local Record on this map yet.'
			await self.instance.gbx.execute('ChatSendServerMessageToLogin', message, player.login)