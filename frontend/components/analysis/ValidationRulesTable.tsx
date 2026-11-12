"use client";

import React from "react";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { RuleResult } from "@/lib/api";

interface ValidationRulesTableProps {
  rules: RuleResult[] | undefined;
}

export function ValidationRulesTable({ rules }: ValidationRulesTableProps) {
  return (
    <div className="border border-slate-800 rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10 text-center">Status</TableHead>
            <TableHead className="w-32">Rule ID</TableHead>
            <TableHead className="w-24">Severity</TableHead>
            <TableHead>Check Description & Message</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rules?.map((rule) => {
            const isPassed = rule.passed;
            const isWarning = rule.severity === "warning";

            return (
              <TableRow key={rule.id}>
                <TableCell className="text-center">
                  {isWarning ? (
                    <AlertTriangle className="w-4 h-4 text-amber-400 inline-block" />
                  ) : isPassed ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 inline-block" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-400 inline-block" />
                  )}
                </TableCell>
                <TableCell className="font-mono text-xs font-semibold text-slate-200">
                  {rule.id}
                </TableCell>
                <TableCell>
                  {isWarning ? (
                    <Badge variant="warning" className="text-[10px]">
                      WARNING
                    </Badge>
                  ) : isPassed ? (
                    <Badge variant="success" className="text-[10px]">
                      PASS
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="text-[10px]">
                      ERROR
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-xs text-slate-300">{rule.message}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

