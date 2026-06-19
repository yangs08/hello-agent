from __future__ import annotations

import json
import os
import unittest
from uuid import uuid4

from app.db import init_db
from app.services.chef import chef_agent


class RunAgentTest(unittest.TestCase):
    def test_real_agent_with_external_image_url(self) -> None:
        init_db()
        image_url = os.getenv(
            "AI_CHEF_TEST_IMAGE_URL",
            "https://inews.gtimg.com/om_bt/OXKPyxDKO0e_cUmPUQmQQKcG539iIL-uj1GKckw5LAmLUAA/1000",
        )
        message = json.dumps(
            {
                "message": "帮我看看这张图里的食材能做什么料理，并找一下相关视频。",
                "url": image_url,
            },
            ensure_ascii=False,
        )

        thread_id = f"test-session-{uuid4().hex}"
        config = {"configurable": {"thread_id": thread_id}}

        response = chef_agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        messages = response.get("messages", [])

        self.assertTrue(messages)
        print(messages[-1].content)


if __name__ == "__main__":
    unittest.main()
