from termlint.config import VerifierConfig
from termlint.core.stages import ProcessingStage
from termlint.verifier.sources.json_glossary import JSONGlossarySource
from termlint.verifier.stages.exact import ExactVerificationStage
from termlint.verifier.stages.fuzzy import FuzzyVerificationStage

from termlint.utils import get_child_logger


logger= get_child_logger('UnifiedPipeline')


class VerifierFactory:

    @staticmethod
    async def create(config: VerifierConfig) -> ProcessingStage:
        """Entrypoint for verifier creation"""

        if not config.source:
            raise ValueError("Verification requires a glossary source. Pass --source or set [tool.termlint.verifier.source].")

        if not config.source.exists():
            raise ValueError(f"Glossary not found: {config.source}")

        logger.info(f"Initializing source: {config.source}")
        source_suffix = config.source.suffix.lower()
        if source_suffix == ".json":
            source = JSONGlossarySource(config.source)
        elif source_suffix in [".ttl", ".rdf"]:
            raise NotImplementedError(f"SPARQL not implemented for {config.source.suffix}")
        else:
            raise ValueError(f"Unknown source format: {source_suffix}")

        source_init_result = await source.initialize()
        if not source_init_result.is_ok:
            raise ValueError(
                f"Failed to initialize glossary source '{config.source}': {'; '.join(source_init_result.errors)}"
            )

        params = config.get_effective_params(config.type)

        match config.type:
            case "exact":
                logger.info("Creating %s", ExactVerificationStage.__name__)
                return ExactVerificationStage(source)
            case "fuzzy":
                logger.info("Creating FuzzyVerificationStage: %s", params)
                return FuzzyVerificationStage(source, **params)
            case _:
                # TODO: may be fallback to exact verification?
                raise ValueError(f"Unknown verifier type: {config.type}")
