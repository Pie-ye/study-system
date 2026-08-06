import unittest

import server


class TeacherStreamParsingTest(unittest.TestCase):
    def test_extracts_visible_content_and_ignores_reasoning(self):
        reasoning = {
            "choices": [{"delta": {"reasoning_content": "internal thought"}}]
        }
        answer = {"choices": [{"delta": {"content": "可見答案"}}]}

        self.assertEqual(server._extract_stream_content(reasoning), "")
        self.assertEqual(server._extract_stream_content(answer), "可見答案")

    def test_extracts_list_text_parts(self):
        chunk = {
            "choices": [
                {
                    "delta": {
                        "content": [
                            {"type": "text", "text": "第一段"},
                            {"type": "text", "text": "第二段"},
                        ]
                    }
                }
            ]
        }

        self.assertEqual(server._extract_stream_content(chunk), "第一段第二段")

    def test_ignores_non_answer_chunks(self):
        self.assertEqual(server._extract_stream_content({}), "")
        self.assertEqual(server._extract_stream_content({"choices": [{"delta": {}}]}), "")


if __name__ == "__main__":
    unittest.main()
