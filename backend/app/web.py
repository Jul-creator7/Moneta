from pathlib import PurePosixPath

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class WebApp(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            target = PurePosixPath(path)
            if (
                error.status_code != 404
                or target.suffix
                or (target.parts and target.parts[0] in {"api", "assets"})
                or scope["method"] not in {"GET", "HEAD"}
            ):
                raise
            response = await super().get_response("index.html", scope)
            response.headers["Cache-Control"] = "no-cache"
            return response
