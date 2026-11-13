from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import done
from app.core.sanitizer import wrap_untrusted_data
from app.schemas.web_search import WebSearchRequest
from app.services.web_search_service import WebSearchService


def register_search_actions(registry: ActionRegistry, search: WebSearchService) -> None:
    def handle_search(parameters: WebSearchRequest):
        res = search.search(parameters)
        data = res.model_dump(mode="json")
        data["answer"] = wrap_untrusted_data(res.answer, source=f"web_search:{parameters.query}")
        return done("web.search", "Web search completed successfully.", data=data)

    registry.register(ActionDefinition(
        action_id="web.search",
        name="Search the web",
        description="Search current web sources and return an answer with source links.",
        category="research",
        parameters=WebSearchRequest,
        handler=handle_search,
        timeout_seconds=45,
        requires_confirmation=True,
    ))
