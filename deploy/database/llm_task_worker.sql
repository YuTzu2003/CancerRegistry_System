IF OBJECT_ID(N''dbo.LLMTaskWorker'', N''U'') IS NULL
BEGIN
    CREATE TABLE dbo.LLMTaskWorker (
        TaskID uniqueidentifier NOT NULL PRIMARY KEY,
        OwnerID nvarchar(128) NOT NULL,
        TaskType nvarchar(32) NOT NULL,
        Status nvarchar(32) NOT NULL,
        ProgressCurrent int NOT NULL CONSTRAINT DF_LLMTaskWorker_ProgressCurrent DEFAULT (0),
        ProgressTotal int NOT NULL CONSTRAINT DF_LLMTaskWorker_ProgressTotal DEFAULT (1),
        AttemptCount int NOT NULL CONSTRAINT DF_LLMTaskWorker_AttemptCount DEFAULT (0),
        PayloadJson nvarchar(max) NOT NULL,
        ErrorMessage nvarchar(max) NULL,
        WorkerID nvarchar(128) NULL,
        NextAttemptAt datetimeoffset NULL,
        CreatedAt datetimeoffset NOT NULL CONSTRAINT DF_LLMTaskWorker_CreatedAt DEFAULT (SYSDATETIMEOFFSET()),
        StartedAt datetimeoffset NULL,
        CompletedAt datetimeoffset NULL,
        UpdatedAt datetimeoffset NOT NULL CONSTRAINT DF_LLMTaskWorker_UpdatedAt DEFAULT (SYSDATETIMEOFFSET())
    );
    CREATE INDEX IX_LLMTaskWorker_Queue ON dbo.LLMTaskWorker (Status, NextAttemptAt, CreatedAt);
    CREATE INDEX IX_LLMTaskWorker_Owner ON dbo.LLMTaskWorker (OwnerID, CreatedAt DESC);
END
IF OBJECT_ID(N''dbo.CK_LLMTaskWorker_TaskType'', N''C'') IS NOT NULL
    ALTER TABLE dbo.LLMTaskWorker DROP CONSTRAINT CK_LLMTaskWorker_TaskType;
ALTER TABLE dbo.LLMTaskWorker WITH CHECK ADD CONSTRAINT CK_LLMTaskWorker_TaskType
    CHECK (TaskType IN (N''chart'', N''compare'', N''annual_report''));