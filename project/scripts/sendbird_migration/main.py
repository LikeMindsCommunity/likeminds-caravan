from project.scripts.sendbird_migration.sendbird_json_migration import SendbirdJsonMigration

users_folder_path = ''
channels_folder_path = ''
messages_folder_path = ''

migration_instance = SendbirdJsonMigration(users_folder_path, channels_folder_path, messages_folder_path)
# migration_instance.migrate_data()
