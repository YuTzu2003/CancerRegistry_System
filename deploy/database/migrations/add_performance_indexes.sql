
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_LLMTaskWorker_TaskType')
    ALTER TABLE [dbo].[LLMTaskWorker] DROP CONSTRAINT [CK_LLMTaskWorker_TaskType];
GO

ALTER TABLE [dbo].[LLMTaskWorker] WITH CHECK ADD CONSTRAINT [CK_LLMTaskWorker_TaskType]
    CHECK (([TaskType]='export_render'
        OR [TaskType]='indicator_report'
        OR [TaskType]='comparison_report'
        OR [TaskType]='annual_report'
        OR [TaskType]='compare'
        OR [TaskType]='chart'));
GO

ALTER TABLE [dbo].[LLMTaskWorker] CHECK CONSTRAINT [CK_LLMTaskWorker_TaskType];
GO


IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_Users_UserID' AND object_id = OBJECT_ID('dbo.Users'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Users_UserID] ON [dbo].[Users] ([UserID] ASC);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_LLMTaskWorker_Status_TaskType_CreatedAt' AND object_id = OBJECT_ID('dbo.LLMTaskWorker'))
    CREATE NONCLUSTERED INDEX [IX_LLMTaskWorker_Status_TaskType_CreatedAt]
        ON [dbo].[LLMTaskWorker] ([Status] ASC, [TaskType] ASC, [CreatedAt] ASC)
        INCLUDE ([OwnerID], [WorkerID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Audit_logs_Action_CreatedAt' AND object_id = OBJECT_ID('dbo.Audit_logs'))
    CREATE NONCLUSTERED INDEX [IX_Audit_logs_Action_CreatedAt]
        ON [dbo].[Audit_logs] ([Action] ASC, [CreatedAt] ASC)
        INCLUDE ([Remote_addr]);
GO
