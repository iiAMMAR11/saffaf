"""Who answers: nobody by default. The Anthropic provider is written and ready, and runs only when the server is
configured for it:

    SAFFAF_ASSIST=anthropic          turn the assistant on
    ANTHROPIC_API_KEY=…              the key (or any credential the Anthropic SDK resolves)
    SAFFAF_ASSIST_MODEL=…            optional; default claude-opus-5-5
    pip install anthropic

Nothing here is called by the trial service: the page shows these features as not enabled. Turning it on also means
telling the user, before the text is sent, that it goes to Anthropic's API (see README.md)."""
import os, json
from assist.tasks import SYSTEM, TASKS, numbered

class AssistantDisabled(Exception):
    pass

class Disabled:
    name = 'disabled'
    def ask(self, task, paragraphs):
        raise AssistantDisabled('المساعد الذكي غير مفعّل في هذا الخادم.')

class Anthropic:
    """Claude through the official SDK, with structured outputs: the answer is JSON that matches the task's schema.
    Not run in this trial (no key, no request); written from the SDK's documented interface."""
    name = 'anthropic'
    def __init__(self, model=None):
        import anthropic   # only when switched on
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get('SAFFAF_ASSIST_MODEL') or 'claude-opus-5-5'
    def ask(self, task, paragraphs):
        t = TASKS[task]
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{'role': 'user', 'content': t['instructions'] + '\n\n' + numbered(paragraphs)}],
            output_config={'effort': t['effort'], 'format': {'type': 'json_schema', 'schema': t['schema']}},
            # a declined request is re-run on another model inside the same call, instead of failing
            betas=['server-side-fallback-2026-07-01'],
            fallbacks='default',
        )
        if response.stop_reason == 'refusal': raise AssistantDisabled('اعتذر المساعد عن هذا النص.')
        if response.stop_reason == 'max_tokens': raise AssistantDisabled('النص أطول مما يتسع له طلب واحد؛ يُقسَّم.')
        text = next(b.text for b in response.content if b.type == 'text')
        return json.loads(text), dict(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)

def provider():
    if os.environ.get('SAFFAF_ASSIST') == 'anthropic': return Anthropic()
    return Disabled()
