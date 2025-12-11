import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  Info,
  FileSearch,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

interface DiligenceDashboardProps {
  findings: any[];
  ddId: string;
}

export function DiligenceDashboard({
  findings,
  ddId,
}: DiligenceDashboardProps) {
  // Calculate statistics
  const stats = React.useMemo(() => {
    const total = findings.length;
    const positive = findings.filter(
      (f) => f.finding_type === "positive"
    ).length;
    const negative = findings.filter(
      (f) => f.finding_type === "negative"
    ).length;
    const gaps = findings.filter((f) => f.finding_type === "gap").length;
    const highConfidence = findings.filter(
      (f) => f.confidence_score >= 0.8
    ).length;
    const requiresAction = findings.filter((f) => f.requires_action).length;

    const riskBreakdown = {
      critical: findings.filter((f) => f.status === "Red").length,
      medium: findings.filter((f) => f.status === "Amber").length,
      low: findings.filter((f) => f.status === "New").length,
      positive: findings.filter((f) => f.status === "Green").length,
    };

    const complianceScore =
      total > 0 ? Math.round((positive / total) * 100) : 0;

    return {
      total,
      positive,
      negative,
      gaps,
      highConfidence,
      requiresAction,
      riskBreakdown,
      complianceScore,
    };
  }, [findings]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4">
      {/* Compliance Score Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Compliance Score
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.complianceScore}%</div>
          <Progress value={stats.complianceScore} className="mt-2" />
          <p className="text-xs text-muted-foreground mt-2">
            Based on {stats.total} findings
          </p>
        </CardContent>
      </Card>

      {/* Findings Breakdown */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <FileSearch className="w-4 h-4" />
            Findings Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm flex items-center gap-1">
                <CheckCircle className="w-3 h-3 text-green-500" />
                Positive
              </span>
              <Badge variant="outline" className="bg-green-50">
                {stats.positive}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm flex items-center gap-1">
                <AlertCircle className="w-3 h-3 text-red-500" />
                Negative
              </span>
              <Badge variant="outline" className="bg-red-50">
                {stats.negative}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm flex items-center gap-1">
                <Info className="w-3 h-3 text-blue-500" />
                Information Gaps
              </span>
              <Badge variant="outline" className="bg-blue-50">
                {stats.gaps}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Distribution */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Risk Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm">Critical</span>
              <Badge className="bg-red-600">
                {stats.riskBreakdown.critical}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Medium</span>
              <Badge className="bg-orange-500">
                {stats.riskBreakdown.medium}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Low</span>
              <Badge className="bg-yellow-500">{stats.riskBreakdown.low}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Items */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <TrendingDown className="w-4 h-4" />
            Action Required
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.requiresAction}</div>
          <p className="text-xs text-muted-foreground mt-2">
            Items requiring immediate attention
          </p>
          <div className="mt-2">
            <Badge variant="destructive" className="text-xs">
              {stats.highConfidence} High Confidence
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
