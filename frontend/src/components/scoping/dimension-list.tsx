"use client";

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { DimensionCard } from "./dimension-card";
import type { DimensionSpec } from "@/lib/mocks/types";
import { useScopingStore } from "@/stores/scoping-store";

interface DimensionListProps {
  dimensions: DimensionSpec[];
}

export function DimensionList({ dimensions }: DimensionListProps) {
  const reorderDimensions = useScopingStore((s) => s.reorderDimensions);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      // Small activation distance so clicks on inner controls don't trigger drag
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const sorted = [...dimensions].sort((a, b) => a.order - b.order);
  const ids = sorted.map((d) => d.id);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = ids.indexOf(String(active.id));
    const newIndex = ids.indexOf(String(over.id));
    if (oldIndex < 0 || newIndex < 0) return;
    const newOrder = arrayMove(ids, oldIndex, newIndex);
    reorderDimensions(newOrder);
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        <ul className="space-y-2.5">
          {sorted.map((d, i) => (
            <li key={d.id}>
              <DimensionCard dimension={d} index={i} />
            </li>
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  );
}
