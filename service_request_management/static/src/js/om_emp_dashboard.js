/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class ServiceDashboard extends Component {
    static template = "ServiceDashboard";

    setup() {
        const today = new Date();

        this.state = useState({
            month: today.getMonth() + 1,
            year: today.getFullYear(),
            monthName: "",
            calendarData: {},
            calendarWeeks: [],
            today: "",
            employees: [],
            fleets: [],
            selectedDate: null,
            selectedServices: [],
            selectedFleetHistory: [],
            availableUsers: [],
            busyUsers: [],
            availableFleets: [],
            busyFleets: [],
            isInitialLoad: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    // ===============================
    // LOAD DATA FROM BACKEND
    // ===============================
    async loadData() {
        const result = await rpc('/service_dashboard/get_data', {
            month: this.state.month,
            year: this.state.year,
        });

        this.state.calendarData = result.calendar_data || {};
        this.state.monthName = result.month_name;
        this.state.today = result.today;
        this.state.employees = result.employees;
        this.state.fleets = result.fleets || [];

        this.buildCalendar();
        
        // Auto-select today's date on initial load
        if (this.state.isInitialLoad) {
            this.selectTodayDate();
            this.state.isInitialLoad = false;
        }
    }

    // ===============================
    // SELECT TODAY'S DATE AUTOMATICALLY
    // ===============================
    selectTodayDate() {
        const todayDateStr = this.state.today;
        
        // Find the cell with today's date
        for (let week of this.state.calendarWeeks) {
            for (let cell of week) {
                if (cell.dateStr === todayDateStr && !cell.isOtherMonth) {
                    this.onDateClick(cell);
                    return;
                }
            }
        }
    }

    // ===============================
    // BUILD CALENDAR GRID
    // ===============================
    buildCalendar() {
        const year = this.state.year;
        const month = this.state.month;

        const firstDay = new Date(year, month - 1, 1);
        let startDay = firstDay.getDay();
        // Adjust for Monday as first day of week (0 = Sunday, 1 = Monday)
        startDay = startDay === 0 ? 6 : startDay - 1;
        
        const daysInMonth = new Date(year, month, 0).getDate();

        let cells = [];

        // empty cells before start
        for (let i = 0; i < startDay; i++) {
            cells.push({ isOtherMonth: true });
        }

        // actual days
        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = `${year}-${String(month).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
            const entries = this.state.calendarData[dateStr] || [];
            
            // Separate services and fleet history
            const services = entries.filter(e => e.type === 'service');
            const fleetHistory = entries.filter(e => e.type === 'fleet');

            cells.push({
                day: d,
                dateStr: dateStr,
                entries: entries,
                services: services,
                fleetHistory: fleetHistory,
                isOtherMonth: false,
                isToday: dateStr === this.state.today,
                isSelected: dateStr === this.state.selectedDate, // ✅ Add selected state
            });
        }

        // split into weeks
        let weeks = [];
        for (let i = 0; i < cells.length; i += 7) {
            weeks.push(cells.slice(i, i + 7));
        }

        this.state.calendarWeeks = weeks;
    }

    // ===============================
    // MONTH NAVIGATION
    // ===============================
    prevMonth() {
        if (this.state.month === 1) {
            this.state.month = 12;
            this.state.year -= 1;
        } else {
            this.state.month -= 1;
        }
        this.loadData();
    }

    nextMonth() {
        if (this.state.month === 12) {
            this.state.month = 1;
            this.state.year += 1;
        } else {
            this.state.month += 1;
        }
        this.loadData();
    }

    // ===============================
    // CLICK DATE → SHOW DETAILS
    // ===============================
    onDateClick(cell) {
        if (!cell || cell.isOtherMonth) return;

        this.state.selectedDate = cell.dateStr;
        this.state.selectedServices = cell.services || [];
        this.state.selectedFleetHistory = cell.fleetHistory || [];

        // Update isSelected for all cells
        this.updateSelectedState();

        // Get all booked user IDs from services and fleet history
        const bookedUserIds = [...(cell.services || []), ...(cell.fleetHistory || [])]
            .map(e => e.user_id)
            .filter(id => id);

        // 🔴 Busy Users
        this.state.busyUsers = this.state.employees.filter(
            emp => bookedUserIds.includes(emp.id)
        );

        // 🟢 Available Users
        this.state.availableUsers = this.state.employees.filter(
            emp => !bookedUserIds.includes(emp.id)
        );
        
        // ✅ Get all booked fleet IDs from services and fleet history
        const bookedFleetIds = [...(cell.services || []), ...(cell.fleetHistory || [])]
            .map(e => e.fleet_id)
            .filter(id => id);
        
        // 🔴 Busy Fleets
        this.state.busyFleets = this.state.fleets.filter(
            fleet => bookedFleetIds.includes(fleet.id)
        );
        
        // 🟢 Available Fleets
        this.state.availableFleets = this.state.fleets.filter(
            fleet => !bookedFleetIds.includes(fleet.id)
        );
    }

    // ===============================
    // UPDATE SELECTED STATE IN CALENDAR
    // ===============================
    updateSelectedState() {
        // Rebuild calendar to update selected state
        const year = this.state.year;
        const month = this.state.month;

        const firstDay = new Date(year, month - 1, 1);
        let startDay = firstDay.getDay();
        startDay = startDay === 0 ? 6 : startDay - 1;
        
        const daysInMonth = new Date(year, month, 0).getDate();

        let cells = [];

        for (let i = 0; i < startDay; i++) {
            cells.push({ isOtherMonth: true });
        }

        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = `${year}-${String(month).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
            const entries = this.state.calendarData[dateStr] || [];
            const services = entries.filter(e => e.type === 'service');
            const fleetHistory = entries.filter(e => e.type === 'fleet');

            cells.push({
                day: d,
                dateStr: dateStr,
                entries: entries,
                services: services,
                fleetHistory: fleetHistory,
                isOtherMonth: false,
                isToday: dateStr === this.state.today,
                isSelected: dateStr === this.state.selectedDate, // ✅ Update selected state
            });
        }

        let weeks = [];
        for (let i = 0; i < cells.length; i += 7) {
            weeks.push(cells.slice(i, i + 7));
        }

        this.state.calendarWeeks = weeks;
    }

    // ===============================
    // ➕ CREATE SERVICE FORM
    // ===============================
    openCreateForm() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Create Service',
            res_model: 'service.request',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
            context: {
                default_scheduled_date: this.state.selectedDate || null,
            }
        });
    }

    // ===============================
    // OPEN SERVICE REQUEST RECORD
    // ===============================
    openServiceRequest(serviceId) {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Service Request',
            res_model: 'service.request',
            res_id: serviceId,
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    // ===============================
    // OPEN FLEET HISTORY RECORD
    // ===============================
    openFleetHistory(fleetHistoryId) {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Fleet History',
            res_model: 'fleet.history',
            res_id: fleetHistoryId,
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    // ===============================
    // GET STYLE FOR SERVICE TYPE
    // ===============================
    getServiceTagStyle(type) {
        if (type === 'fleet') {
            return 'ed-service-tag-fleet';
        }
        return 'ed-service-tag';
    }
}

// REGISTER ACTION
registry.category("actions").add("service_dashboard", ServiceDashboard);