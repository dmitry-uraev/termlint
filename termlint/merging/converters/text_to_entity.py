"""
Convert TextEntityStream to EntityStream
"""


from termlint.core.types import EntityStream, TextEntityStream


class TextToEntityConverter:

    async def convert(self, input_stream: TextEntityStream) -> EntityStream:
        ...
