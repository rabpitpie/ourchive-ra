from ourchiveao3importer.work_list import WorkList
from ourchiveao3importer.works import Work
from ourchiveao3importer.chapters import Chapters
import uuid
from etl.models import WorkImport, ObjectMapping
from api import models as api
from django.utils.translation import gettext as _

class EtlWorkImport(object):

	def __init__(self, user_id, save_as_draft=False, allow_anon_comments=False, allow_comments=True):
		self.save_as_draft = save_as_draft
		self.allow_anon_comments = allow_anon_comments
		self.allow_comments = allow_comments
		self.user_id = user_id
		self.error_message = ''
		self.success_message = 'Your work(s) have finished importing.'

	def get_works_by_username(self, username):
		self.work_list = WorkList(username)
		self.work_list.find_work_ids()
		for work_id in self.work_list.work_ids:
			import_job = self.create_import_job(work_id)
		return True

	def run_unprocessed_jobs(self):
		import_jobs = WorkImport.objects.filter(job_finished=False).filter(job_processing=False).order_by('created_on')[:100]
		for job in import_jobs:
			self.import_job = job
			self.user_id = job.user.id 
			self.save_as_draft = job.save_as_draft
			self.allow_anon_comments = job.allow_anon_comments
			self.allow_comments = job.allow_comments
			self.get_single_work(job.work_id, True, job)
		self.handle_job_complete(1, self.import_job)

	def get_single_work(self, work_id, as_batch=False, import_job=None):
		if not as_batch:
			import_job = self.create_import_job(work_id)
		if import_job:
			chapters_processed = self.import_work(self.import_job.job_uid)
			if not as_batch or not chapters_processed:
				# if it's a single import or the import failed, let's go ahead and create a notif.
				# this prevents spamming on success of a username import
				self.handle_job_complete(chapters_processed, self.import_job)

	def create_import_job(self, work_id):
		job_uid = uuid.uuid4()
		import_job = WorkImport(
			job_uid=job_uid, 
			work_id=work_id, 
			allow_comments=self.allow_comments, 
			allow_anon_comments=self.allow_anon_comments,
			save_as_draft=self.save_as_draft,
			user_id=self.user_id
		)
		import_job.save()
		self.import_job = import_job
		return True

	def handle_job_complete(self, process_signal, import_job):
		if process_signal is None:
			self.handle_job_fail(import_job)
			print("work import failed. returning")
			return
		self.handle_job_success(import_job)
		print("work import complete")

	def import_work(self, job_uid):
		import_job = WorkImport.objects.filter(job_uid=job_uid).first()
		work_id = import_job.work_id
		if api.Work.objects.filter(external_id=work_id).first() is not None:
			return 0
		# handle restricted & 404 errors here
		work_importer = Work(work_id)
		work_dict = work_importer.__dict__()
		work_processed_id = self.process_work_data(work_dict)
		if work_processed_id is None:
			self.handle_job_fail(import_job)
			return
		chapters = Chapters(work_id)
		chapters.chapter_contents()
		chapter_dict = chapters.__dict__() if chapters else {}
		chapters_processed = self.process_chapter_data(chapter_dict, work_processed_id)
		return chapters_processed

	def process_mappings(self, obj, mappings, origin_json):
		for mapping in mappings:
			if "." in mapping.origin_field:
				# we only need to support depth 2 here
				mapping_split = mapping.origin_field.split(".")
				origin_value = origin_json[mapping_split[0]][mapping_split[1]]
			else:
				origin_value = origin_json[mapping.origin_field]
			if origin_value is None:
				continue
			if 'tag' in mapping.destination_field:
				# create tag
				tag_type_label = mapping.destination_field.split(".")[1]
				tag_type = api.TagType.objects.filter(label=tag_type_label).first()
				if not tag_type:
					tag_type = api.TagType(label=tag_type_label)
					tag_type.save()
				if type(origin_value) is list:
					for text in origin_value:
						tag = api.Tag.objects.filter(text=text.lower()).first()
						if not tag:
							tag = api.Tag(text=text.lower(), display_text=text, tag_type=tag_type)
							tag.save()
						obj.tags.add(tag)
				else:
					tag = api.Tag.objects.filter(text=origin_value.lower()).first()
					if not tag:
						tag = api.Tag(text=origin_value.lower(), display_text=origin_value, tag_type=tag_type)
						tag.save()
					obj.tags.add(tag)
			elif 'attribute' in mapping.destination_field:
				# create attribute
				attribute_type_label = mapping.destination_field.split(".")[1]
				attribute_type = api.AttributeType.objects.filter(name=attribute_type_label.lower()).first()
				if not attribute_type:
					attribute_type = api.AttributeType(
						name=attribute_type_label.lower(), 
						display_name=attribute_type_label,
						allow_on_work=True,
						allow_on_bookmark=True,
						allow_on_chapter=True)
					attribute_type.save()
				if type(origin_value) is list:
					for attribute_value in origin_value:
						obj_attr = api.AttributeValue.objects.filter(name=attribute_value.lower()).first()
						if not obj_attr:
							obj_attr = api.AttributeValue(
								name=attribute_value.lower(), 
								display_name=attribute_value,
								attribute_type=attribute_type)
							obj_attr.save()
						obj.attributes.add(obj_attr)
				else:
					obj_attr = api.AttributeValue.objects.filter(name=origin_value.lower()).first()
					if not work_attr:
						obj_attr = api.AttributeValue(
							name=origin_value.lower(), 
							display_name=origin_value,
							attribute_type=attribute_type)
						obj_attr.save()
					obj.attributes.add(obj_attr)
			else:
				setattr(obj, mapping.destination_field, origin_value)
		obj.save()
		return obj.id

	def process_work_data(self, work_json):
		mappings = ObjectMapping.objects.filter(import_type='ao3', object_type='work').all()
		work = api.Work(
			user_id=self.user_id, 
			comments_permitted=self.allow_comments, 
			anon_comments_permitted=self.allow_anon_comments, 
			draft=self.save_as_draft,
			is_complete=True,
			external_id=self.import_job.work_id)
		work.save()
		return self.process_mappings(work, mappings, work_json)
		

	def process_chapter_data(self, chapter_json, work_id):
		mappings = ObjectMapping.objects.filter(import_type='ao3', object_type='chapter').all()
		chapter_ids = []
		chapter_num = 1
		for chapter_content in chapter_json['content']:
			chapter = api.Chapter(work_id=work_id, user_id=self.user_id, number=chapter_num)
			chapter.save()
			chapter_ids.append(self.process_mappings(chapter, mappings, chapter_content))
			chapter_num += 1
		return chapter_ids

	# TODO handle failure
	def create_fail_notification(self):
		user = api.User.objects.filter(id=self.user_id).first()
		notification_type = api.NotificationType.objects.filter(
		type_label="System Notification").first()
		notification = api.Notification.objects.create(notification_type=notification_type, user=user, title=_("Work Import Processed"),
			content=_("Your work import has been processed. You can view your works in your profile."))
		notification.save()
		user.has_notifications = True
		user.save()

	def create_success_notification(self):
		user = api.User.objects.filter(id=self.user_id).first()
		notification_type = api.NotificationType.objects.filter(
		type_label="System Notification").first()
		notification = api.Notification.objects.create(notification_type=notification_type, user=user, title=_("Work Import Processed"),
			content=_("Your work import has been processed. You can view your works in your profile."))
		notification.save()
		user.has_notifications = True
		user.save()

	def handle_job_fail(self, import_job):
		import_job = WorkImport.objects.get(pk=import_job.id)
		import_job.job_message = self.error_message
		import_job.job_success = False
		import_job.job_processing = False
		import_job.job_finished = True
		import_job.save()
		self.create_fail_notification()

	def handle_job_success(self, import_job):
		import_job = WorkImport.objects.get(pk=import_job.id)
		import_job.job_message = self.success_message
		import_job.job_success = True
		import_job.job_finished = True
		import_job.job_processing = False
		import_job.save()
		self.create_success_notification()
