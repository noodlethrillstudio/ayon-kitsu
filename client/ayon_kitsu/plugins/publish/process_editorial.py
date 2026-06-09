# -*- coding: utf-8 -*-
import re

import gazu
import pyblish.api

from ayon_kitsu.pipeline import KitsuPublishContextPlugin

class ProcessKitsuEditorial(KitsuPublishContextPlugin):
    """Process Kitsu Editorial Task Creation/ selection"""

    order = pyblish.api.IntegratorOrder
    label = "Process Kitsu Editorial"
    families = ["kitsu"]
    task_redirect = "Animatic_Ref"

    def generate_tasks(self, context):
        """Generate kitsu tasks for the shot if they don't exist."""
        return


    def process(self, context):
        for instance in context:
            self.log.debug("Processing editorial review comment.")

            kitsu_entity = instance.data.get("kitsuEntity")
            shot_id = kitsu_entity.get("id") if kitsu_entity else None
            self.log.debug(f"Kitsu shot id from instance data: {shot_id}")
            if not shot_id:
                self.log.debug(
                    "No shot id found in instance data, "
                    "cannot find task for review comment."
                )
                continue

            task_type = gazu.task.get_task_type_by_name(self.task_redirect)
            kitsu_task = gazu.task.get_task_by_name(kitsu_entity, task_type)
            if kitsu_task:
                kitsu_task = gazu.task.get_task(kitsu_task["id"])

            self.log.debug(f"Found task: {kitsu_task['id']}") if kitsu_task else self.log.debug("No task found")
            if not kitsu_task:  
                self.log.debug("No task found for editorial review comment.")
                continue

            instance.data["kitsuTask"] = kitsu_task
