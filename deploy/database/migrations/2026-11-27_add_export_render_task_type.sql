-- Background export render queue reuses dbo.LLMTaskWorker with a new
-- TaskType='export_render'. The CK_LLMTaskWorker_TaskType check constraint must
-- allow that value, otherwise INSERTs from create_export_task() fail.
--
-- Run ONCE against the hospital database during deploy. Idempotent and
-- reversible (re-add the original constraint without 'export_render' to roll back).
-- No data is changed.

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
