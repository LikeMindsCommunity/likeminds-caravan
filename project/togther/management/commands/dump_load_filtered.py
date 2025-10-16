import json
import uuid
import os

from django.conf import settings
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.models import ForeignKey
from django.forms.models import model_to_dict
from togther.models import ModelUtilities

from external_services.amazon_s3.s3_client_impl import S3ClientImpl

INCLUDED_APPS = ["togther", "auth", "collabmates_api"]
INCLUDED_MODELS = [
    'auth.user',
    'togther.community',
    'togther.userinfo',
    'togther.report_tags',
    'togther.conversationpolls',
    'togther.conversationpollmembers',
    'togther.conversationeventmembers',
    'togther.conversationeventnudge',
    'togther.conversationmemberstate',
    'togther.card_attachment',
    'togther.answerattachment',
    'togther.category',
    'togther.attributes',
    'togther.collabcardpolls',
    'togther.memberpollvotes',
    'togther.communitytype',
    'togther.communitysubtype',
    'togther.masterquestions',
    'togther.emailtokens',
    'togther.useremails',
    'togther.usermobiles',
    'togther.mobilebackup',
    'togther.communityfieldtypes',
    'togther.communityfieldsubtypes',
    'togther.communityfield',
    'togther.adminrights',
    'togther.memberrights',
    'togther.userdevices',
    # 'togther.homesnackbar',
    # 'togther.usersurvey',
    'togther.messagereactions',
    'togther.communityuserdelete',
    'togther.cohortmember',
    'togther.cohortrights',
    'togther.cohortfilter',
    'togther.directmessagetutorial',
    'togther.getstarted',
    'togther.chatroomsecrettypeconversion',
    'togther.chatroominvite',
    'togther.userchannelsettings',
    'togther.activeuser',
    'collabmates_api.communityemailconfiguration',
    'collabmates_api.whatsappsubscription',
    'togther.communitybillingdates',
    'collabmates_api.sdkclient'
]

LOAD_MODEL_LABELS_ORDERED = [
    # Independent models
    'auth.user',
    'togther.report_tags',
    'togther.category',
    'togther.communitytype',
    'togther.mobilebackup',
    'togther.communityfieldtypes',
    'togther.adminrights',
    'togther.memberrights',
    'togther.getstarted',
    'togther.community',
    'togther.messagetemplate',

    # Models depending only on auth.user, togther.community
    'togther.userinfo',
    'togther.communitytoast',
    'togther.members',
    'togther.removedmembers',
    'togther.temp_admin',
    'togther.community_lpig',
    'togther.community_rank',
    'togther.referal',
    'togther.collabcard',
    'togther.draftchatroom',
    'togther.deletedchatrooms',
    'togther.card_answers',
    'togther.collabcardstate',
    'togther.conversationengage',
    'togther.report',
    'togther.collabcardstatebackup',
    'togther.collabcardtemp',
    'togther.communityquestions',
    'togther.communityanswers',
    'togther.communityexpire',
    'togther.questionfilters',
    'togther.communityexpirycodes',
    'togther.createcommunityaction',
    'togther.communitylevels',
    'togther.communityupdate',
    'togther.conversationpolls',
    'togther.communitysubtype',
    'togther.communityfieldsubtypes',
    'togther.member_engage',
    'togther.community_legacy',
    'togther.community_profession',
    'togther.community_interest',
    'togther.community_geography',
    'togther.membersengagepilot',
    'togther.memberspilot',
    'togther.membernotificationflag',
    'togther.useradminrights',
    'togther.usermemberrights',
    'togther.moderationhistory',
    'togther.communityrightssettings',
    'togther.blockedmembers',
    'togther.usermemberrightshistory',
    'togther.subscriptionexpiredmembers',
    'togther.eventnudge',
    'togther.contentdownloadsettings',
    'togther.cohort',
    'togther.communitysettings',
    'togther.communitytoastv1',
    'togther.communityjoinemail',
    'togther.communitygetstarted',
    'togther.useremailssendstatus',
    'togther.communitydirectmessagesettings',
    'togther.sdkclientusersinfo',
    'togther.communitynotificationsettings',
    'togther.feednotificationsettings',
    'togther.communitybillingdates',
    'togther.communityconfigurations',
    'togther.chatbotmeta',
    'togther.blockuser',
    'togther.communityintegrationstatus',
    'collabmates_api.sdkclient',
    'collabmates_api.sdkplatform',
    'collabmates_api.sdkonboardingscreen',
    'collabmates_api.communitywebhook',
    'collabmates_api.connectionrequest',
    'collabmates_api.connection',
    'togther.conversationpollmembers',
    'togther.conversationeventmembers',
    'togther.conversationeventnudge',
    'togther.conversationmemberstate',
    'togther.card_attachment',
    'togther.answerattachment',
    'togther.attributes',
    'togther.collabcardpolls',
    'togther.memberpollvotes',
    'togther.masterquestions',
    'togther.emailtokens',
    'togther.useremails',
    'togther.usermobiles',
    'togther.communityfield',
    'togther.userdevices',
    'togther.homesnackbar',
    'togther.usersurvey',
    'togther.messagereactions',
    'togther.communityuserdelete',
    'togther.cohortmember',
    'togther.cohortrights',
    'togther.cohortfilter',
    'togther.directmessagetutorial',
    'togther.chatroomsecrettypeconversion',
    'togther.chatroominvite',
    'togther.userchannelsettings',
    'togther.activeuser',
    'collabmates_api.communityemailconfiguration',
    'collabmates_api.whatsappsubscription'
]


class Command(BaseCommand):
    help = "Dump all models filtered by community_id, with schema dependencies."

    def _get_model_label(self, model):
        return f"{model._meta.app_label}.{model._meta.model_name}"

    def _get_schema_maps(self, all_models):
        schema_fk_map = {}
        schema_map = {}

        for model in all_models:
            if model._meta.app_label not in INCLUDED_APPS:
                continue

            model_label = self._get_model_label(model)
            fks = {}
            for field in model._meta.fields:
                if isinstance(field, ForeignKey):
                    related_model = field.remote_field.model
                    fks[field.name] = self._get_model_label(related_model)
            schema_fk_map[model_label] = fks
            schema_map[model_label] = model

        return schema_fk_map, schema_map

    def _dump_model_streaming(self, model, file_path, filter_dict, model_ids_map, user_id_field_names, user_ids,
                              chunk_size=100000):
        """
        Dumps model data incrementally into a single JSON file.
        Appends data for each model to the same JSON file without holding everything in memory.
        """

        model_label = self._get_model_label(model)
        queryset = model.objects.filter(**filter_dict)
        count = queryset.count()

        self.stdout.write(self.style.NOTICE(f"Dumping {model_label} for filter: {filter_dict} ({count} records)..."))

        filename = f"{'/'.join([file_path, model_label.replace('.', '_')])}.json"
        write_mode = "a" if os.path.exists(filename) else "w"

        pk_id_list = []

        with open(filename, write_mode, encoding="utf-8") as f:
            if write_mode == "w":
                f.write("{")

            # Add comma if file already has content
            if f.tell() > 1:
                f.write(",\n")

            f.write(f'"{model_label}": {{')
            first = True

            for obj in queryset.iterator(chunk_size=chunk_size):
                data = model_to_dict(obj)
                # Replace FKs with just their PKs
                for field in model._meta.fields:

                    if isinstance(field, ForeignKey):
                        data[field.name] = getattr(obj, f"{field.name}_id", None)

                        if field.name in user_id_field_names and data[field.name]:
                            user_ids.add(data[field.name])

                    if field.name == "id":
                        value = getattr(obj, f"{field.name}", None)

                        if isinstance(value, uuid.UUID):
                            value = str(value)
                            data[field.name] = value
                        #
                        # if model_label == "togther.cohort" and value:
                        #     cohort_ids.add(value)
                        #
                        # elif model_label == "togther.card_answers" and value:
                        #     conversation_ids.add(value)

                pk_value = obj.pk

                if isinstance(pk_value, uuid.UUID):
                    pk_value = str(pk_value)

                pk_id_list.append(pk_value)

                if not first:
                    f.write(",")
                json.dump(str(pk_value), f)
                f.write(":")
                json.dump(data, f, default=str)
                first = False

            f.write("}}")

        model_ids_map[model_label] = pk_id_list

        self.stdout.write(self.style.SUCCESS(f"Done: {model_label} ({count} records)"))

        return filename

    def _dump_model(self, model, community_id, schema_fk_map, model_ids_map={}, user_ids=set(),
                    chunk_size=10000):
        model_label = self._get_model_label(model)
        field_names = [f.name for f in model._meta.get_fields()]
        filter_dict = {}
        user_id_field_names = []
        community_billing_ids = model_ids_map.get("togther.communitybillingdates", [])

        file_path = "community_data_dump"

        for fk_field, related_model_label in schema_fk_map.get(model_label, {}).items():
            records_list = model_ids_map.get(related_model_label, [])

            if records_list:
                filter_dict[f"{fk_field}__in"] = records_list

            if related_model_label == "auth.user":
                user_id_field_names.append(fk_field)

        # build filter
        if model_label == "togther.community":
            filter_dict = {
                "id": community_id
            }

        elif model_label == "togther.communityuserdelete":
            filter_dict = {
                "deleted_community_id": community_id
            }

        elif model_label == "collabmates_api.communityemailconfiguration":
            filter_dict = {
                "sdk_client__community_id": community_id
            }

        elif "community" in field_names:
            filter_dict = {
                "community": community_id
            }

        elif "community_id" in field_names:
            filter_dict = {
                "community_id": community_id
            }

        else:
            if model_label == "auth.user" and user_ids:
                filter_dict["id__in"] = user_ids

            elif model_label == "togther.activeuser":
                filter_dict["billing_id__in"] = community_billing_ids

        self._dump_model_streaming(model, file_path, filter_dict, model_ids_map, user_id_field_names,
                                   user_ids, chunk_size=chunk_size)

        return file_path

    def _dump_data(self, community_id):
        dump_data = {}
        model_ids_map = {}
        user_ids = set()

        self.stdout.write(self.style.WARNING(f"Starting filtered dump for community_id={community_id}"))

        all_models = apps.get_models()
        total_models = len(all_models)
        self.stdout.write(self.style.SUCCESS(f"Found {total_models} models."))

        schema_fk_map, schema_map = self._get_schema_maps(all_models)

        # Step 2: Determine models linked to community
        community_models = []
        independent_models = []
        other_models = []
        user_models = []

        for model in all_models:
            if model._meta.app_label not in INCLUDED_APPS:
                continue

            model_label = self._get_model_label(model)

            field_names = [f.name for f in model._meta.get_fields()]
            if "community" in field_names or "community_id" in field_names:
                community_models.append(model)
            else:
                if model_label in INCLUDED_MODELS:
                    if not schema_fk_map.get(model_label, {}) and model_label not in [
                        "togther.community", "auth.user", "togther.emailtokens"
                    ]:
                        independent_models.append(model)

                    else:
                        if model_label not in ["togther.userinfo", "auth.user", "togther.emailtokens",
                                               "togther.usermobiles", "togther.useremails", "togther.userdevices",
                                               "togther.directmessagetutorial", "collabmates_api.whatsappsubscription"]:
                            other_models.append(model)

        for model_label in ["auth.user", "togther.userinfo", "togther.emailtokens", "togther.usermobiles",
                            "togther.useremails", "togther.userdevices", "togther.directmessagetutorial",
                            "collabmates_api.whatsappsubscription"]:
            user_models.append(schema_map.get(model_label))

        output_dir = ""

        # Step 4: Dump each model
        for models in [community_models, other_models, independent_models, user_models]:

            for model in models:
                output_dir = self._dump_model(model, community_id, schema_fk_map, model_ids_map, user_ids)

        # Step 5: Save dump file
        # filename = f"data_dump_{community_id}.json"
        json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]

        # for file_name in json_files:
        #     file_path = os.path.join(output_dir, file_name)
        #     with open(file_path, "r", encoding="utf-8") as f:
        #         data = json.load(f)
        #         dump_data.update(data)

        # with open(filename, "w+") as f:
        #     json.dump(dump_data, f, indent=4, default=str)

        # Upload the JSON file to S3
        bucket = settings.S3_BUCKETS.get("sendbird_migration")

        s3_client = S3ClientImpl(bucket)

        for filename in json_files:
            file_path = os.path.join(output_dir, filename)
            # with open(file_path, "r", encoding="utf-8") as f:
            #     data = json.load(f)
            #     dump_data.update(data)
            uploaded = s3_client.upload_file_to_s3_bucket(
                object_path=file_path,
                file_path=f"{community_id}/database_dump/json/{filename}",
            )

            if uploaded:
                self.stdout.write(self.style.SUCCESS(
                    f"Uploaded database dump to S3 at {bucket}/{community_id}/database_dump/json/{filename}"
                ))
            else:
                self.stdout.write(self.style.ERROR("Failed to upload database dump to S3."))

            # Remove the local file
            self.stdout.write(self.style.NOTICE("Removing local dump file..."))
            os.remove(file_path)

    def _load_model(self, model, data, schema_fk_map):
        model_label = self._get_model_label(model)
        model_data = data.get(model_label, {})
        bulk_create_list = []

        if not model_data:
            return

        self.stdout.write(self.style.NOTICE(f"Loading {model_label} ({len(model_data)} records)..."))

        # Identify M2M fields
        m2m_fields = [f.name for f in model._meta.many_to_many]
        self_fk_fields = []  # self FKs

        # Phase 1 — Create all instances without self FKs
        deferred_self_fks = []  # (instance, fk_field, target_pk)

        for pk, record in model_data.items():
            if "id" in record:
                del record["id"]

            # --- Handle FKs ---
            for fk_field, related_label in schema_fk_map.get(model_label, {}).items():
                if fk_field in record and record[fk_field] is not None:
                    if related_label == model_label:
                        self_fk_fields.append(fk_field)

                        # self-FK → handle later
                        deferred_self_fks.append((pk, fk_field, record[fk_field]))
                        record[fk_field] = None
                        continue

                    related_data = data.get(related_label, {})
                    related_instance = related_data.get(str(record[fk_field]))
                    record[fk_field] = related_instance if related_instance else None

            # --- Handle M2M ---
            m2m_values = {}
            for f_name in m2m_fields:
                if f_name in record:
                    m2m_values[f_name] = record.pop(f_name)

            # --- Create instance ---
            instance = model(**record)
            instance._pending_m2m = m2m_values
            instance._original_pk = pk
            bulk_create_list.append(instance)

        # --- Bulk create ---
        ModelUtilities.bulk_create_instances(model, bulk_create_list)

        # --- Update model_data with instances ---
        for instance in bulk_create_list:
            model_data[str(instance._original_pk)] = instance

        # Phase 2: Resolve self-FKs (only if model actually has them)
        if self_fk_fields and deferred_self_fks:
            for pk, fk_field, target_pk in deferred_self_fks:
                instance = model_data.get(str(pk))
                target_instance = model_data.get(str(target_pk))
                if instance and target_instance:
                    setattr(instance, fk_field, target_instance)

            model.objects.bulk_update(
                [model_data[str(pk)] for pk, _, _ in deferred_self_fks],
                self_fk_fields
            )

            self.stdout.write(
                self.style.SUCCESS(f"Updated {len(deferred_self_fks)} self-FKs for {model_label}")
            )

        # --- Handle many-to-many fields ---
        for instance in bulk_create_list:
            if hasattr(instance, "_pending_m2m"):
                for f_name, values in instance._pending_m2m.items():
                    if not values:
                        continue
                    try:
                        getattr(instance, f_name).set(values)
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"M2M set failed for {model_label}.{f_name}: {e}")
                        )

                del instance._pending_m2m
                del instance._original_pk

        self.stdout.write(self.style.SUCCESS(f"Done: {model_label} loaded ({len(model_data)} records)"))

    def _load_data(self, file_path):
        if not file_path:
            self.stdout.write(self.style.ERROR("file_path is required for loading data"))
            return

        self.stdout.write(self.style.WARNING(f"Starting loading from file_path={file_path}"))

        with open(file_path, "r") as f:
            load_data = json.load(f)

        all_models = apps.get_models()
        schema_fk_map, _ = self._get_schema_maps(all_models)

        for model in all_models:
            self._load_model(model, load_data, schema_fk_map)

    def add_arguments(self, parser):
        parser.add_argument("--community_id", type=int, help="Community ID to filter data for")
        parser.add_argument("--action_type", type=str, help="Whether to dump or load data (dump/load)")
        parser.add_argument("--file_path", type=str, help="Path to the JSON file for loading data")

    def handle(self, *args, **options):
        community_id = options["community_id"]
        action_type = options["action_type"]
        file_path = options.get("file_path")

        if action_type == "dump":
            self._dump_data(community_id)

        elif action_type == "load":
            self._load_data(file_path)
