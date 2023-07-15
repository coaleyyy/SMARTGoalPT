from uuid import uuid4

from beanie import PydanticObjectId
from beanie.odm.operators.update.array import Push
from beanie.odm.operators.update.general import Set
from bson import ObjectId

from app.exceptions import (
    DuplicateGoalError,
    NoGoalsFoundError,
    NoRecordsUpdatedError,
    UserNotFoundError,
)
from app.models.user import Goal, GoalCreate, User
from app.services.user_service import get_full_user


async def create_goal(user_id: ObjectId | PydanticObjectId, goal: GoalCreate) -> list[Goal]:
    user = await get_full_user(user_id)

    if not user:
        raise UserNotFoundError("No user with the id {user_id} found")

    if await get_goal_by_name(user_id, goal.name):
        raise DuplicateGoalError(f"A goal with the name {goal.name} already exists")

    goal_insert = Goal(
        id=str(uuid4()),
        name=goal.name.strip(),
        duration=goal.duration,
        days_of_week=goal.days_of_week,
        repeats_every=goal.repeats_every,
        progress=goal.progress,
    )

    if user.goals:
        update_result = await User.find_one(User.id == user_id).update(
            Push({User.goals: goal_insert})
        )
    else:
        update_result = await user.find_one(User.id == user_id).update(
            Set({User.goals: [goal_insert]})
        )

    if update_result.modified_count < 1:  # pragma: no cover
        raise NoRecordsUpdatedError(f"Error adding goal {goal.name} to user {user_id}")

    updated_user = await User.find_one(User.id == user.id)

    if not updated_user:  # pragma: no cover
        raise UserNotFoundError(f"User {user_id} not found after update")

    if not updated_user.goals:  # pragma: no cover
        raise NoGoalsFoundError(f"User {user_id} has no goals")

    return updated_user.goals


async def get_goal_by_id(user_id: ObjectId | PydanticObjectId, goal_id: str) -> Goal | None:
    user = await get_full_user(user_id)

    if not user:
        raise UserNotFoundError("No user with the id {user_id} found")

    if not user.goals:
        return None

    for goal in user.goals:
        if goal.id == goal_id:
            return goal

    return None


async def get_goal_by_name(user_id: ObjectId | PydanticObjectId, goal_name: str) -> Goal | None:
    user = await get_full_user(user_id)

    if not user:
        raise UserNotFoundError("No user with the id {user_id} found")

    if not user.goals:
        return None

    for goal in user.goals:
        if goal.name == goal_name:
            return goal

    return None


async def get_goals_by_user_id(user_id: ObjectId | PydanticObjectId) -> list[Goal] | None:
    user = await User.find_one(User.id == user_id)

    if not user or not user.goals:
        return None

    return user.goals
