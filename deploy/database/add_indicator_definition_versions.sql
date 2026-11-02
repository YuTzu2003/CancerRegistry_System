SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.IndicatorDefinitionVersion', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.IndicatorDefinitionVersion (
        version_id int IDENTITY(1,1) NOT NULL PRIMARY KEY,
        version_name nvarchar(100) NOT NULL,
        version_description nvarchar(1000) NULL,
        status nvarchar(20) NOT NULL CONSTRAINT DF_IndicatorDefinitionVersion_Status DEFAULT N'DRAFT',
        rules_json nvarchar(max) NOT NULL,
        created_by nvarchar(100) NOT NULL,
        created_at datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_by nvarchar(100) NULL,
        updated_at datetime2 NULL,
        published_by nvarchar(100) NULL,
        published_at datetime2 NULL,
        CONSTRAINT UQ_IndicatorDefinitionVersion_Name UNIQUE (version_name),
        CONSTRAINT CK_IndicatorDefinitionVersion_Json CHECK (ISJSON(rules_json) = 1),
        CONSTRAINT CK_IndicatorDefinitionVersion_Status CHECK (status IN (N'DRAFT', N'PENDING', N'PUBLISHED', N'INACTIVE'))
    );

    -- Each old per-cancer version is retained as an explicitly partial definition.
    -- Missing cancer definitions must be added in maintenance before analysis.
    IF OBJECT_ID(N'dbo.IndicatorRuleVersion', N'U') IS NOT NULL
    BEGIN
        EXEC sys.sp_executesql N'
            SET IDENTITY_INSERT dbo.IndicatorDefinitionVersion ON;
            INSERT INTO dbo.IndicatorDefinitionVersion
                (version_id, version_name, status, rules_json, created_by, created_at)
            SELECT version_id,
                LEFT(version_name, 70) + N''〔舊版#'' + CONVERT(nvarchar(12), version_id) + N''〕'',
                N''PUBLISHED'',
                N''{"'' + STRING_ESCAPE(cancer_group_key, ''json'') + N''":'' + rules_json + N''}'',
                created_by, created_at
            FROM dbo.IndicatorRuleVersion;
            SET IDENTITY_INSERT dbo.IndicatorDefinitionVersion OFF;';
    END
END

-- Upgrade databases created before the rule-version workflow was introduced.
IF COL_LENGTH(N'dbo.IndicatorDefinitionVersion', N'version_description') IS NULL
    ALTER TABLE dbo.IndicatorDefinitionVersion ADD version_description nvarchar(1000) NULL;

IF COL_LENGTH(N'dbo.IndicatorDefinitionVersion', N'status') IS NULL
BEGIN
    EXEC sys.sp_executesql N'ALTER TABLE dbo.IndicatorDefinitionVersion ADD status nvarchar(20) NULL;';
END

-- Run these in separate dynamic batches. SQL Server otherwise compiles the
-- UPDATE against the old table shape before it runs ALTER TABLE ADD.
-- This remains safe to re-run if a previous deployment stopped part-way through.
EXEC sys.sp_executesql N'UPDATE dbo.IndicatorDefinitionVersion SET status = N''PUBLISHED'' WHERE status IS NULL;';

IF EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID(N'dbo.IndicatorDefinitionVersion')
      AND name = N'status' AND is_nullable = 1
)
    EXEC sys.sp_executesql N'ALTER TABLE dbo.IndicatorDefinitionVersion ALTER COLUMN status nvarchar(20) NOT NULL;';

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.IndicatorDefinitionVersion')
      AND name = N'DF_IndicatorDefinitionVersion_Status'
)
    EXEC sys.sp_executesql N'ALTER TABLE dbo.IndicatorDefinitionVersion ADD CONSTRAINT DF_IndicatorDefinitionVersion_Status DEFAULT N''DRAFT'' FOR status;';

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.IndicatorDefinitionVersion')
      AND name = N'CK_IndicatorDefinitionVersion_Status'
)
    EXEC sys.sp_executesql N'ALTER TABLE dbo.IndicatorDefinitionVersion ADD CONSTRAINT CK_IndicatorDefinitionVersion_Status CHECK (status IN (N''DRAFT'', N''PENDING'', N''PUBLISHED'', N''INACTIVE''));';

IF COL_LENGTH(N'dbo.IndicatorDefinitionVersion', N'updated_by') IS NULL
    ALTER TABLE dbo.IndicatorDefinitionVersion ADD updated_by nvarchar(100) NULL;
IF COL_LENGTH(N'dbo.IndicatorDefinitionVersion', N'updated_at') IS NULL
    ALTER TABLE dbo.IndicatorDefinitionVersion ADD updated_at datetime2 NULL;
IF COL_LENGTH(N'dbo.IndicatorDefinitionVersion', N'published_by') IS NULL
    ALTER TABLE dbo.IndicatorDefinitionVersion ADD published_by nvarchar(100) NULL;
IF COL_LENGTH(N'dbo.IndicatorDefinitionVersion', N'published_at') IS NULL
    ALTER TABLE dbo.IndicatorDefinitionVersion ADD published_at datetime2 NULL;

IF OBJECT_ID(N'dbo.IndicatorDefinitionVersionHistory', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.IndicatorDefinitionVersionHistory (
        history_id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        version_id int NOT NULL,
        action nvarchar(40) NOT NULL,
        status_before nvarchar(20) NULL,
        status_after nvarchar(20) NULL,
        rules_before_json nvarchar(max) NULL,
        rules_after_json nvarchar(max) NULL,
        change_reason nvarchar(1000) NULL,
        changed_by nvarchar(100) NOT NULL,
        changed_at datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT CK_IndicatorDefinitionVersionHistory_BeforeJson CHECK (rules_before_json IS NULL OR ISJSON(rules_before_json) = 1),
        CONSTRAINT CK_IndicatorDefinitionVersionHistory_AfterJson CHECK (rules_after_json IS NULL OR ISJSON(rules_after_json) = 1)
    );
    CREATE INDEX IX_IndicatorDefinitionVersionHistory_VersionChangedAt
        ON dbo.IndicatorDefinitionVersionHistory (version_id, changed_at DESC);
END

COMMIT TRANSACTION;
