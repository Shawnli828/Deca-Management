from server_modules.account_issues import apply_zero_play_issues as apply_zero_play_issues_impl
from server_modules.db_core import upsert_row as upsert_row_impl
from server_modules.reelfarm_lifecycle import (
    active_tiktok_automation_account_ids as active_tiktok_automation_account_ids_impl,
    mark_missing_reelfarm_automations as mark_missing_reelfarm_automations_impl,
)
from server_modules.schema import relational_table_counts as relational_table_counts_impl


class ReelFarmProjectionRepository:
    def __init__(self, conn, *, placeholder):
        self.conn = conn
        self.placeholder = placeholder

    def upsert_row(self, table, values, conflict_cols, update_cols=None):
        return upsert_row_impl(
            self.conn,
            table,
            values,
            conflict_cols,
            self.placeholder,
            update_cols,
        )

    def active_tiktok_automation_account_ids(self, account_ids):
        return active_tiktok_automation_account_ids_impl(
            self.conn,
            account_ids,
            placeholder=self.placeholder,
        )

    def mark_missing_reelfarm_automations(self, product_market_channel_id, seen_reelfarm_ids, synced_at):
        return mark_missing_reelfarm_automations_impl(
            self.conn,
            product_market_channel_id,
            seen_reelfarm_ids,
            synced_at,
            placeholder=self.placeholder,
        )

    def apply_zero_play_issues(self, candidates, synced_at):
        def upsert(conn, table, values, conflict_cols, update_cols=None):
            return upsert_row_impl(conn, table, values, conflict_cols, self.placeholder, update_cols)

        def active_account_ids(conn, account_ids):
            return active_tiktok_automation_account_ids_impl(
                conn,
                account_ids,
                placeholder=self.placeholder,
            )

        return apply_zero_play_issues_impl(
            self.conn,
            candidates,
            synced_at,
            placeholder=self.placeholder,
            upsert_row=upsert,
            active_tiktok_automation_account_ids=active_account_ids,
        )

    def table_counts(self):
        return relational_table_counts_impl(self.conn)
