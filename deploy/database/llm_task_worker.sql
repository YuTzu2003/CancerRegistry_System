-- For an existing table, run `uv run python -m modules.services.migrate_llm_task_files`
-- before this script so existing payloads and progress are preserved in task.json.
IF OBJECT_ID(N'dbo.LLMTaskWorker', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.LLMTaskWorker (
        TaskID uniqueidentifier NOT NULL PRIMARY KEY,
        OwnerID nvarchar(128) NOT NULL,
        TaskType nvarchar(32) NOT NULL,
        Status nvarchar(32) NOT NULL,
        ProgressTotal int NOT NULL CONSTRAINT DF_LLMTaskWorker_ProgressTotal DEFAULT (1),
        WorkerID nvarchar(128) NULL,
        CreatedAt datetimeoffset NOT NULL CONSTRAINT DF_LLMTaskWorker_CreatedAt DEFAULT (SYSDATETIMEOFFSET()),
        CompletedAt datetimeoffset NULL
    );
END
ELSE
BEGIN
    DECLARE @DropDefaults nvarchar(max) = N'';

    SELECT @DropDefaults += N'ALTER TABLE dbo.LLMTaskWorker DROP CONSTRAINT ' + QUOTENAME(default_constraint.name) + N';'
    FROM sys.default_constraints AS default_constraint
    INNER JOIN sys.columns AS column_info
        ON column_info.object_id = default_constraint.parent_object_id
        AND column_info.column_id = default_constraint.parent_column_id
    WHERE default_constraint.parent_object_id = OBJECT_ID(N'dbo.LLMTaskWorker')
      AND column_info.name IN (N'ProgressCurrent', N'AttemptCount', N'PayloadJson', N'ErrorMessage', N'NextAttemptAt', N'StartedAt', N'UpdatedAt');

    IF @DropDefaults <> N'' EXEC sp_executesql @DropDefaults;

    IF COL_LENGTH(N'dbo.LLMTaskWorker', N'ProgressCurrent') IS NOT NULL
        ALTER TABLE dbo.LLMTaskWorker DROP COLUMN ProgressCurrent;
    IF COL_LENGTH(N'dbo.LLMTaskWorker', N'AttemptCount') IS NOT NULL
        ALTER TABLE dbo.LLMTaskWorker DROP COLUMN AttemptCount;
    IF COL_LENGTH(N'dbo.LLMTaskWorker', N'PayloadJson') IS NOT NULL
        ALTER TABLE dbo.LLMTaskWorker DROP COLUMN PayloadJson;
    IF COL_LENGTH(N'dbo.LLMTaskWorker', N'ErrorMessage') IS NOT NULL
        ALTER TABLE dbo.LLMTaskWorker DROP COLUMN ErrorMessage;
    IF COL_LENGTH(N'dbo.LLMTaskWorker', N'NextAttemptAt') IS NOT NULL
        ALTER TABLE dbo.LLMTaskWorker DROP COLUMN NextAttemptAt;
    IF COL_LENGTH(N'dbo.LLMTaskWorker', N'StartedAt') IS NOT NULL
        ALTER TABLE dbo.LLMTaskWorker DROP COLUMN StartedAt;
    IF COL_LENGTH(N'dbo.LLMTaskWorker', N'UpdatedAt') IS NOT NULL
        ALTER TABLE dbo.LLMTaskWorker DROP COLUMN UpdatedAt;
END

IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.LLMTaskWorker') AND name = N'IX_LLMTaskWorker_Queue')
    DROP INDEX IX_LLMTaskWorker_Queue ON dbo.LLMTaskWorker;
CREATE INDEX IX_LLMTaskWorker_Queue ON dbo.LLMTaskWorker (Status, CreatedAt);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.LLMTaskWorker') AND name = N'IX_LLMTaskWorker_Owner')
    CREATE INDEX IX_LLMTaskWorker_Owner ON dbo.LLMTaskWorker (OwnerID, CreatedAt DESC);

IF OBJECT_ID(N'dbo.CK_LLMTaskWorker_TaskType', N'C') IS NOT NULL
    ALTER TABLE dbo.LLMTaskWorker DROP CONSTRAINT CK_LLMTaskWorker_TaskType;
ALTER TABLE dbo.LLMTaskWorker WITH CHECK ADD CONSTRAINT CK_LLMTaskWorker_TaskType
    CHECK (TaskType IN (N'chart', N'compare', N'annual_report', N'comparison_report'));
