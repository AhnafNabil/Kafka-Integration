from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Any, Dict, Optional

from app.db.postgresql import get_db
from app.models.user import (
    User, UserUpdate, UserResponse, UserChangePassword,
    Address, AddressCreate, AddressUpdate, AddressResponse
)
from app.api.dependencies import get_current_user, get_user_by_id
from app.core.security import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user profile.
    """
    # Load addresses explicitly to avoid lazy loading issues
    result = await db.execute(select(Address).where(Address.user_id == current_user.id))
    addresses = result.scalars().all()
    
    # Construct response manually
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        addresses=[
            AddressResponse(
                id=addr.id,
                line1=addr.line1,
                line2=addr.line2,
                city=addr.city,
                state=addr.state,
                postal_code=addr.postal_code,
                country=addr.country,
                is_default=addr.is_default
            ) for addr in addresses
        ]
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update current user profile.
    """
    # Update only provided fields
    update_data = user_update.dict(exclude_unset=True)
    
    if update_data:
        for key, value in update_data.items():
            setattr(current_user, key, value)
        
        await db.commit()
        await db.refresh(current_user)
    
    # Load addresses explicitly
    result = await db.execute(select(Address).where(Address.user_id == current_user.id))
    addresses = result.scalars().all()
    
    # Construct response manually
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        addresses=[
            AddressResponse(
                id=addr.id,
                line1=addr.line1,
                line2=addr.line2,
                city=addr.city,
                state=addr.state,
                postal_code=addr.postal_code,
                country=addr.country,
                is_default=addr.is_default
            ) for addr in addresses
        ]
    )


@router.put("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_change: UserChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Change user password.
    """
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/me/addresses", response_model=List[AddressResponse])
async def get_user_addresses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get all addresses for the current user.
    """
    result = await db.execute(select(Address).where(Address.user_id == current_user.id))
    addresses = result.scalars().all()
    
    return [
        AddressResponse(
            id=addr.id,
            line1=addr.line1,
            line2=addr.line2,
            city=addr.city,
            state=addr.state,
            postal_code=addr.postal_code,
            country=addr.country,
            is_default=addr.is_default
        ) for addr in addresses
    ]


@router.post("/me/addresses", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_user_address(
    address: AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new address for the current user.
    """
    # If this is the first address or it's set as default
    is_first_address = False
    if address.is_default:
        # Check if the user already has a default address
        result = await db.execute(
            select(Address).where(
                Address.user_id == current_user.id,
                Address.is_default == True
            )
        )
        current_default = result.scalars().first()
        
        if current_default:
            # Remove default flag from the current default address
            current_default.is_default = False
    else:
        # Check if this is the first address (make it default automatically)
        result = await db.execute(
            select(Address).where(Address.user_id == current_user.id)
        )
        if not result.scalars().first():
            is_first_address = True
    
    # Create the new address
    db_address = Address(
        user_id=current_user.id,
        line1=address.line1,
        line2=address.line2,
        city=address.city,
        state=address.state,
        postal_code=address.postal_code,
        country=address.country,
        is_default=address.is_default or is_first_address
    )
    
    db.add(db_address)
    await db.commit()
    await db.refresh(db_address)
    
    return AddressResponse(
        id=db_address.id,
        line1=db_address.line1,
        line2=db_address.line2,
        city=db_address.city,
        state=db_address.state,
        postal_code=db_address.postal_code,
        country=db_address.country,
        is_default=db_address.is_default
    )


@router.get("/me/addresses/{address_id}", response_model=AddressResponse)
async def get_user_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a specific address for the current user.
    """
    result = await db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id
        )
    )
    address = result.scalars().first()
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address with ID {address_id} not found",
        )
    
    return AddressResponse(
        id=address.id,
        line1=address.line1,
        line2=address.line2,
        city=address.city,
        state=address.state,
        postal_code=address.postal_code,
        country=address.country,
        is_default=address.is_default
    )


@router.get("/{user_id}/verify", response_model=Dict[str, Any])
async def verify_user_exists(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Verify if a user exists and is active.
    This endpoint is used by other services to validate users.
    """
    user = await get_user_by_id(db, user_id)
    
    if not user or not user.is_active:
        return {"valid": False}
    
    return {
        "valid": True,
        "user_id": user.id,
        "email": user.email,
        "full_name": f"{user.first_name} {user.last_name}"
    }