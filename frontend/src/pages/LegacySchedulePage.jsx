// frontend/src/pages/LegacySchedulePage.jsx
import { useState, useEffect } from "react";
import EditableDataTable from "../components/EditableDataTable";
import ScheduleTable from "../components/ScheduleTable";
import ExplanationPanel from "../components/ExplanationPanel";
import {
  startWorkflow,
  runStep2,
  runStep3,
  runStep4,
  runStep5,
  finalizeWorkflow,
  updateWorkflowStep,
} from "../api/workflowApi";
import "./LegacySchedulePage.css";

// ... تعریف WorkflowStepper (همان کد قبلی)
// ... تعریف SchedulePage (همان کد قبلی)

export default function LegacySchedulePage(props) {
  // همان محتوای SchedulePage قبلی
}