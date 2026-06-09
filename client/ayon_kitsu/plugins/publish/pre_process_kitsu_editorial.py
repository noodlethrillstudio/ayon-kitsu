# -*- coding: utf-8 -*-
import gazu
import pyblish.api

from ayon_kitsu.pipeline import KitsuPublishContextPlugin
from ayon_core.pipeline import KnownPublishError


class GenerateKitsuEditorial(KitsuPublishContextPlugin):
    """This script essentially replicates collect_kitsu_entities, but will first check if the instance is an editorial and build missing tasks if so.
    should ideally be merged with collect kitsu entities. Have not merged/ changed collector logic as feature may be studio specific."""


    order = pyblish.api.CollectorOrder + 0.498
    label = "Generate Kitsu Editorial Tasks"
    task_redirect = "Animatic_Ref"

    def generate_tasks(self, context):
        """Generate kitsu tasks for the shot if they don't exist."""
        return

    def process(self, context):
        if not self.task_redirect:
            self.log.debug("No task redirect set, skipping editorial task generation.")
            return
        project_entity = context.data["projectEntity"]
        project_id = project_entity["data"].get("kitsuProjectId")
        kitsu_project = None
        if project_id:
            kitsu_project = gazu.project.get_project(project_id)
        if not kitsu_project:
            project_name = context.data["projectName"]
            raise KnownPublishError(
                f"Project '{project_name}' not found in kitsu by id!"
            )

        context.data["kitsuProject"] = kitsu_project
        self.log.debug(f"Collect kitsu project: {kitsu_project}")

        filtered_instances = []
        for instance in context:
            folder_entity = instance.data.get("folderEntity")
            if folder_entity:
                filtered_instances.append(instance)

        if not filtered_instances:
            return

        kitsu_entities_by_id = {}
        self.log.debug(f"Processing {len(filtered_instances)} instances for potential editorial task generation.")
        for instance in filtered_instances:
            if "editorial" not in (instance.data.get("creator_identifier") or ""):
                self.log.debug("Creator flag not editorial.")
                continue
            folder_entity = instance.data["folderEntity"]
            folder_path = folder_entity["path"]
            kitsu_id = folder_entity["data"].get("kitsuId")
            if kitsu_id:
                self.log.debug(f"Kitsu id found in AYON for '{folder_path}', skipping shot and task generation.")
                continue
            if not kitsu_id:
                self.log.debug(
                    f"Kitsu id not available in AYON for '{folder_path}', generating shot and tasks."
                )
                shot_name = instance.data.get("shotName") or folder_entity["name"]
                episode_name = None
                sequence_name = None

                parents = instance.data.get("parents")
                for parent in parents:
                    # {'entity_type': 'folder', 'folder_type': 'Episode', 'entity_name': 'ep148_icec_old'}
                    if parent.get("entity_type") == "folder" and parent.get("folder_type") == "Episode":
                        episode_name = parent.get("entity_name") 
                        #{'entity_type': 'folder', 'folder_type': 'sequence', 'entity_name': 'sc01'}
                        continue
                    if parent.get("entity_type") == "folder" and parent.get("folder_type") == "sequence":
                        sequence_name = parent.get("entity_name")
                        continue
                kitsu_episode = gazu.shot.get_episode_by_name(kitsu_project, episode_name)
                self.log.debug(f"Kitsu episode name from instance data: {episode_name}")
                if not kitsu_episode:
                    raise KnownPublishError(
                        f"Episode '{episode_name}' not found in kitsu, cannot generate shot and tasks for editorial review."
                    )
                kitsu_sequence = gazu.shot.get_sequence_by_name(kitsu_project, sequence_name, episode=kitsu_episode)
                if not kitsu_sequence:
                    self.log.debug(f"Sequence '{sequence_name}' not found in kitsu, generating sequence.")
                    kitsu_sequence = gazu.shot.new_sequence(kitsu_project, sequence_name, episode=kitsu_episode)
                else:
                    self.log.debug(f"Found sequence '{sequence_name}' in kitsu.")

                kitsu_shot = gazu.shot.get_shot_by_name(kitsu_sequence, shot_name)
                if not kitsu_shot:
                    self.log.debug(f"Shot '{shot_name}' not found in kitsu, generating shot.")
                    kitsu_shot = gazu.shot.new_shot(kitsu_project, kitsu_sequence, shot_name, nb_frames = None, frame_in = None, frame_out = None, description = None, data = None)
                else:
                    self.log.debug(f"Found shot '{shot_name}' in kitsu.")

                # Make generated/located shot available for the current publish run.
                # AYON folder data persistence is handled separately.
                folder_entity["data"]["kitsuId"] = kitsu_shot["id"]
                instance.data["kitsuEntity"] = kitsu_shot
                kitsu_entities_by_id[kitsu_shot["id"]] = kitsu_shot

                # Ensure the redirect task type exists on the shot and cache it
                # for the same publish run. Downstream plugins look this up by
                # task type and expect the default task name pattern.
                redirect_task_type = gazu.task.get_task_type_by_name(
                    self.task_redirect
                )
                if not redirect_task_type:
                    raise KnownPublishError(
                        f"Task type '{self.task_redirect}' not found in Kitsu."
                    )

                redirect_task = gazu.task.get_task_by_name(
                    kitsu_shot, redirect_task_type
                )
                if not redirect_task:
                    todo = gazu.task.get_task_status_by_name("ToDo")
                    redirect_task = gazu.task.new_task(
                        kitsu_shot,
                        redirect_task_type,
                        name="main",
                        task_status=todo,
                    )
                if redirect_task:
                    instance.data["kitsuTask"] = redirect_task