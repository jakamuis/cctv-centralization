import asyncio
import yaml

from sqlalchemy import select

from app.db.session import get_async_session_maker
from app.models.branch import Branch
from app.models.camera import Camera


GO2RTC_CONFIG = "go2rtc/go2rtc.yaml"

BRANCH_NAME = "SIG Kendal"
BRANCH_CODE = "SIG-KENDAL"
BRANCH_LOCATION = "Kendal"


def extract_channel(rtsp_url: str) -> str:
    try:
        return rtsp_url.split("/Streaming/Channels/")[1]
    except Exception:
        return "unknown"


def load_go2rtc_config():
    with open(GO2RTC_CONFIG, "r") as f:
        return yaml.safe_load(f)


async def get_or_create_branch(session):
    result = await session.execute(
        select(Branch).where(Branch.code == BRANCH_CODE)
    )

    branch = result.scalar_one_or_none()

    if branch:
        return branch

    branch = Branch(
        name=BRANCH_NAME,
        code=BRANCH_CODE,
        location=BRANCH_LOCATION,
    )

    session.add(branch)

    await session.commit()
    await session.refresh(branch)

    print(f"[+] Created branch: {branch.name}")

    return branch


async def camera_exists(session, stream_name: str):
    result = await session.execute(
        select(Camera).where(Camera.stream_name == stream_name)
    )

    return result.scalar_one_or_none()


async def import_cameras():

    config = load_go2rtc_config()

    streams = config.get("streams", {})

    async_session_maker = get_async_session_maker()

    async with async_session_maker() as session:

        branch = await get_or_create_branch(session)

        imported = 0
        skipped = 0

        for stream_name, stream_config in streams.items():

            existing = await camera_exists(session, stream_name)

            if existing:
                print(f"[SKIP] Duplicate: {stream_name}")
                skipped += 1
                continue

            rtsp_url = stream_config.get("url")

            if not rtsp_url:
                print(f"[SKIP] No RTSP URL: {stream_name}")
                skipped += 1
                continue

            rtsp_channel = extract_channel(rtsp_url)

            camera = Camera(
                branch_id=branch.id,
                name=stream_name.replace("-", " ").title(),
                stream_name=stream_name,
                rtsp_channel=rtsp_channel,
                status="UNKNOWN",
                enabled=True,
            )

            session.add(camera)

            print(f"[+] Imported: {stream_name}")

            imported += 1

        await session.commit()

        print("")
        print("===================================")
        print("IMPORT COMPLETE")
        print("===================================")
        print(f"Imported : {imported}")
        print(f"Skipped  : {skipped}")


if __name__ == "__main__":
    asyncio.run(import_cameras())