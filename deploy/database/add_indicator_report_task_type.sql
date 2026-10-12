IF OBJECT_ID(N'dbo.LLMTaskWorker', N'U') IS NOT NULL
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sys.check_constraints
        WHERE parent_object_id = OBJECT_ID(N'dbo.LLMTaskWorker')
          AND name = N'CK_LLMTaskWorker_TaskType'
    )
        ALTER TABLE dbo.LLMTaskWorker DROP CONSTRAINT CK_LLMTaskWorker_TaskType;

    ALTER TABLE dbo.LLMTaskWorker WITH CHECK
        ADD CONSTRAINT CK_LLMTaskWorker_TaskType CHECK (
            TaskType IN ('chart', 'compare', 'annual_report', 'comparison_report', 'indicator_report')
        );
    ALTER TABLE dbo.LLMTaskWorker CHECK CONSTRAINT CK_LLMTaskWorker_TaskType;
END;
