"""Contrato HTTP de /api/chat com alternância real dos fornecedores, sem API paga."""
import io
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib import request
from urllib.error import HTTPError

import key_rotation
import thigas_wiki
import web_cloud


class HTTPCloudRotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),web_cloud.Handler)
        cls.server.daemon_threads=True
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)

    def setUp(self):
        key_rotation._reset_for_tests()
        with web_cloud.RATE_LOCK:
            web_cloud.CALL_TIMES.clear()

    def chat(self,prompt):
        body=json.dumps({
            "modo":"mini","esforco":"equilibrado","pergunta":prompt,
            "wikipedia":False,"historico":[]
        }).encode("utf-8")
        url=f"http://127.0.0.1:{self.server.server_port}/api/chat"
        req=request.Request(
            url,data=body,method="POST",
            headers={"Content-Type":"application/json"}
        )
        with request.urlopen(req,timeout=20) as response:
            return json.load(response)

    def test_http_responses_alternate_without_exposing_keys(self):
        env={
            "THIGAS_CLOUD_MODE":"1",
            "MARITACA_API_KEY":"maritaca-secret",
            "GROQ_API_KEY":"groq-first",
            "GROQ_API_KEY_2":"groq-second",
            "MARITACA_MODEL":"sabiazinho-4-br-sp",
            "GROQ_MODEL":"openai/gpt-oss-20b",
            "THIGAS_MAX_REQUESTS_HOUR":"20",
        }
        calls=[]
        def fake_upstream(url, **opts):
            calls.append((url,opts["headers"]["Authorization"],opts["data"]["model"]))
            return {"choices":[{"message":{"content":"Resposta válida em português."}}]}
        with patch.dict(os.environ,env,clear=True), \
             patch.object(web_cloud.Handler,"authorized",return_value=True), \
             patch.object(thigas_wiki,"http_json",side_effect=fake_upstream):
            answers=[self.chat("Pergunta "+str(i)) for i in range(4)]
            status=request.urlopen(request.Request(
                f"http://127.0.0.1:{self.server.server_port}/api/status"
            ))
            with status:
                status=json.load(status)
        self.assertEqual([c["resposta"] for c in answers],["Resposta válida em português."]*4)
        self.assertEqual(
            [x[0] for x in calls],[
                "https://chat.maritaca.ai/api/chat/completions",
                "https://api.groq.com/openai/v1/chat/completions",
                "https://chat.maritaca.ai/api/chat/completions",
                "https://api.groq.com/openai/v1/chat/completions",
            ]
        )
        self.assertEqual([x[1] for x in calls],[
            "Bearer maritaca-secret","Bearer groq-first",
            "Bearer maritaca-secret","Bearer groq-second",
        ])
        self.assertEqual(status["rotacao"]["chaves"],3)
        self.assertTrue(status["rotacao"]["ativa"])
        for text in [json.dumps(answers),json.dumps(status)]:
            for secret in ("maritaca-secret","groq-first","groq-second"):
                self.assertNotIn(secret,text)
        self.assertEqual(status["limites_saida"]["equilibrado"],1150)

    def test_http_failover_from_429_to_maridaca(self):
        env={
            "THIGAS_CLOUD_MODE":"1",
            "MARITACA_API_KEY":"m-secret",
            "GROQ_API_KEY":"g-secret",
            "GROQ_API_KEY_2":"g-other",
            "THIGAS_MAX_REQUESTS_HOUR":"20",
        }
        seen=[]
        def fake_upstream(url,**opts):
            seen.append((url,opts["headers"]["Authorization"]))
            if "groq.com" in url:
                raise thigas_wiki.THIGASError("429") from HTTPError(
                    url,429,"Too Many Requests",{"Retry-After":"120"},io.BytesIO(b"")
                )
            return {"choices":[{"message":{"content":"Fallback funcionou."}}]}
        with patch.dict(os.environ,env,clear=True), \
             patch.object(web_cloud.Handler,"authorized",return_value=True), \
             patch.object(thigas_wiki,"http_json",side_effect=fake_upstream):
            self.chat("Primeira")
            result=self.chat("Segunda")
            result2=self.chat("Terceira")
        self.assertEqual(result["resposta"],"Fallback funcionou.")
        self.assertEqual(result2["resposta"],"Fallback funcionou.")
        self.assertEqual(sum("groq.com" in url for url,_ in seen),1)
        self.assertNotIn("g-secret",json.dumps(result))


if __name__=="__main__":
    unittest.main()
