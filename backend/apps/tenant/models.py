"""
SentinelX - 租户管理数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index, ForeignKey, UniqueConstraint
from apps.core.database import Base


class Tenant(Base):
    """租户模型"""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True, index=True)
    slug = Column(String(64), nullable=False, unique=True, index=True)

    # 租户配置 (JSONB)
    config = Column(JSON, default=dict)

    # API Token (加密存储)
    api_token = Column(String(256), nullable=True)

    # 配额限制
    max_alerts = Column(Integer, default=10000)  # 最大告警数
    max_users = Column(Integer, default=10)  # 最大用户数
    max_rules = Column(Integer, default=100)  # 最大规则数
    max_channels = Column(Integer, default=20)  # 最大渠道数
    alert_qps = Column(Integer, default=100)  # 告警接入QPS限制

    # 状态
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"


class User(Base):
    """用户模型 - 支持多租户"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # 基本信息
    username = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(256), nullable=False, unique=True, index=True)
    phone = Column(String(32), nullable=True)

    # 密码 (加密存储)
    password_hash = Column(String(256), nullable=False)

    # 用户类型
    is_system = Column(Boolean, default=False)  # 系统管理员（不受租户限制）
    is_superuser = Column(Boolean, default=False)  # 租户管理员（在本租户内）

    # 状态
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # 最后登录
    last_login_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class UserTenant(Base):
    """用户-租户关联表（多对多）"""

    __tablename__ = "user_tenants"
    __table_args__ = (
        UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant'),
        Index('idx_user_tenant_user', 'user_id'),
        Index('idx_user_tenant_tenant', 'tenant_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # 用户在该租户中的角色ID
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    # 是否为当前活跃租户（切换用）
    is_current = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Role(Base):
    """角色模型"""

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'code', name='uq_role_tenant_code'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)  # null表示系统级角色

    name = Column(String(64), nullable=False)
    code = Column(String(64), nullable=False)  # 如: admin, viewer, system_admin
    description = Column(Text, nullable=True)

    # 权限列表 (JSON)
    permissions = Column(JSON, default=list)

    # 内置角色不可删除
    is_builtin = Column(Boolean, default=False)

    # scope: system / tenant
    scope = Column(String(32), default="tenant")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name}, code={self.code})>"


class Team(Base):
    """团队/业务组模型"""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)

    name = Column(String(128), nullable=False)
    code = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)

    # 负责人
    leader_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Team(id={self.id}, name={self.name})>"


class UserTeam(Base):
    """用户团队关联"""

    __tablename__ = "user_teams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    team_id = Column(Integer, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """审计日志"""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_tenant_time", "tenant_id", "created_at"),
        Index("idx_audit_user_time", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(64), nullable=False)

    # 操作信息
    action = Column(String(64), nullable=False)  # create/update/delete/login等
    resource_type = Column(String(64), nullable=False)  # alert/rule/user等
    resource_id = Column(String(128), nullable=True)

    # 详情
    details = Column(JSON, default=dict)

    # 来源
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(256), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
