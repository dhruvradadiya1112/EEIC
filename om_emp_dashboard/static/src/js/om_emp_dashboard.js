/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";


export class EmployeeDashboard extends Component {
    static template = "EmployeeDashboardMain";
    static props = ["*"];

    setup() {
        this.notificationService = useService("notification");

        const today = new Date();
        this.state = useState({
            month: today.getMonth() + 1,
            year: today.getFullYear(),
            monthName: "",
            calendarData: {},
            kpi: {},
            upcomingHolidays: [],
            upcomingBirthdays: [],
            currentEmployeeName: "",
            isLoading: true,
            isCalendarLoading: false,
            calendarWeeks: [],
            today: "",
        });

        onWillStart(async () => {
            await this._fetchDashboardData();
        });
    }

    /**
     * Full fetch - called once on initial load.
     */
    async _fetchDashboardData() {
        this.state.isLoading = true;
        try {
            const result = await rpc(
                "/om_emp_dashboard/get_dashboard_data",
                {
                    month: this.state.month,
                    year: this.state.year,
                }
            );
            this._applyResult(result, true);
        } catch (error) {
            this.notificationService.add(
                _t("Failed to load dashboard data"),
                { type: "danger" }
            );
        }
        this.state.isLoading = false;
    }

    /**
     * Calendar-only fetch - called when navigating months.
     */
    async _fetchCalendarData() {
        this.state.isCalendarLoading = true;
        try {
            const result = await rpc(
                "/om_emp_dashboard/get_dashboard_data",
                {
                    month: this.state.month,
                    year: this.state.year,
                }
            );
            this._applyResult(result, false);
        } catch (error) {
            this.notificationService.add(
                _t("Failed to load calendar data"),
                { type: "danger" }
            );
        }
        this.state.isCalendarLoading = false;
    }

    /**
     * Apply server result to state.
     */
    _applyResult(result, full) {
        this.state.calendarData = result.calendar_data || {};
        this.state.monthName = result.month_name;
        this.state.today = result.today;
        this._buildCalendarWeeks();

        if (full) {
            this.state.kpi = result.kpi || {};
            this.state.upcomingHolidays = result.upcoming_holidays || [];
            this.state.upcomingBirthdays = result.upcoming_birthdays || [];
            this.state.currentEmployeeName = result.current_employee_name;
        }
    }

    /* ---- Calendar grid builder ---- */

    _buildCalendarWeeks() {
        const TOTAL_WEEKS = 6;
        const TOTAL_CELLS = TOTAL_WEEKS * 7;

        const year = this.state.year;
        const month = this.state.month;
        const firstDay = new Date(year, month - 1, 1);
        const lastDay = new Date(year, month, 0);
        const daysInMonth = lastDay.getDate();
        const startDow = firstDay.getDay();
        const startOffset = (startDow + 6) % 7; // Monday = 0

        const prevLastDay = new Date(year, month - 1, 0);
        const prevDaysInMonth = prevLastDay.getDate();

        const cells = [];

        for (let i = startOffset - 1; i >= 0; i--) {
            const d = prevDaysInMonth - i;
            const dt = new Date(year, month - 2, d);
            cells.push(this._makeDayCell(dt, true));
        }

        for (let d = 1; d <= daysInMonth; d++) {
            const dt = new Date(year, month - 1, d);
            cells.push(this._makeDayCell(dt, false));
        }

        let nextDay = 1;
        while (cells.length < TOTAL_CELLS) {
            const dt = new Date(year, month, nextDay);
            cells.push(this._makeDayCell(dt, true));
            nextDay++;
        }

        const weeks = [];
        for (let i = 0; i < cells.length; i += 7) {
            weeks.push(cells.slice(i, i + 7));
        }

        this.state.calendarWeeks = weeks;
    }

    /**
     * Build a single calendar cell object.
     */
    _makeDayCell(dt, isOther) {
        const y = dt.getFullYear();
        const m = dt.getMonth() + 1;
        const d = dt.getDate();
        const dateStr =
            y + "-" + String(m).padStart(2, "0") + "-" + String(d).padStart(2, "0");

        const dayData = this.state.calendarData[dateStr] || null;
        const entries = dayData ? (dayData.entries || []) : [];
        const isWorkingDay = dayData ? dayData.is_working_day : true;
        const expectedHours = dayData ? dayData.expected_hours : 0;
        const dayStatus = dayData ? dayData.day_status : "";
        const holidays = dayData ? (dayData.holidays || []) : [];
        const isPublicHoliday = dayData ? (dayData.is_public_holiday || false) : false;

        let totalHours = 0;
        for (const e of entries) {
            totalHours += e.worked_hours || 0;
        }

        // Build holiday display name (first holiday only for space)
        let holidayName = "";
        if (holidays.length > 0) {
            holidayName = holidays[0].name;
            if (holidays.length > 1) {
                holidayName += " +" + (holidays.length - 1);
            }
        }

        return {
            day: d,
            dateStr: dateStr,
            entries: entries,
            totalHours: totalHours,
            expectedHours: expectedHours,
            isToday: dateStr === this.state.today,
            hasData: entries.length > 0,
            isOtherMonth: isOther,
            isWorkingDay: isWorkingDay,
            dayStatus: dayStatus,
            holidays: holidays,
            isPublicHoliday: isPublicHoliday,
            holidayName: holidayName,
        };
    }

    /* ---- Helpers used in template ---- */

    formatHours(hours) {
        if (!hours && hours !== 0) return "0h 00m";
        const h = Math.floor(hours);
        const m = Math.round(Math.abs(hours - h) * 60);
        return h + "h " + String(m).padStart(2, "0") + "m";
    }

    getDayClass(cell) {
        if (!cell) return "ed-day-empty";
        let cls = "ed-day-cell";
        if (cell.isOtherMonth) cls += " ed-day-other-month";
        if (cell.dayStatus === "before_joining") cls += " ed-day-before-joining";
        if (cell.isToday) cls += " ed-day-today";
        if (!cell.isOtherMonth && cell.isPublicHoliday) cls += " ed-day-public-holiday";
        else if (!cell.isOtherMonth && !cell.isWorkingDay) cls += " ed-day-off";
        if (cell.hasData) {
            cls += " ed-day-has-data";
            if (cell.totalHours > 0 && cell.totalHours >= cell.expectedHours) {
                cls += " ed-day-full-hours";
            } else if (cell.totalHours > 0 && cell.expectedHours > 0 && cell.totalHours < cell.expectedHours) {
                cls += " ed-day-low-hours";
            }
        }
        if (!cell.isOtherMonth && cell.dayStatus === "absent") {
            cls += " ed-day-absent";
        }
        return cls;
    }

    getStatusLabel(status) {
        const labels = {
            present: "Present",
            absent: "Absent",
            day_off: "Day Off",
            half_day: "Half Day",
            short_day: "Short Day",
            holiday: "Off Day",
            public_holiday: "Holiday",
            today_pending: "In Progress",
            upcoming: "Upcoming",
            before_joining: "Not Joined",
        };
        return labels[status] || status;
    }

    getStatusClass(status) {
        const classes = {
            present: "ed-status-present",
            absent: "ed-status-absent",
            day_off: "ed-status-dayoff",
            half_day: "ed-status-halfday",
            short_day: "ed-status-shortday",
            holiday: "ed-status-holiday",
            public_holiday: "ed-status-public-holiday",
            today_pending: "ed-status-present",
            upcoming: "ed-status-upcoming",
            before_joining: "ed-status-before-joining",
        };
        return classes[status] || "ed-status-absent";
    }

    getHolidayTypeLabel(type) {
        const labels = {
            public: "Public",
            company: "Company",
            optional: "Optional",
            restricted: "Restricted",
        };
        return labels[type] || type;
    }

    /* ---- Event handlers ---- */

    async onPrevMonth(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.state.month === 1) {
            this.state.month = 12;
            this.state.year -= 1;
        } else {
            this.state.month -= 1;
        }
        await this._fetchCalendarData();
    }

    async onNextMonth(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.state.month === 12) {
            this.state.month = 1;
            this.state.year += 1;
        } else {
            this.state.month += 1;
        }
        await this._fetchCalendarData();
    }

}

registry.category("actions").add("om_emp_dashboard_main", EmployeeDashboard);
