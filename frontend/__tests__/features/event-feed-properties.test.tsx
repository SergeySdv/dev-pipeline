/**
 * Property-Based Tests for Event Feed Component
 * **Feature: frontend-comprehensive-refactor**
 *
 * Property 13: Event feed filtering consistency
 * Property 14: Event feed protocol links
 *
 * **Validates: Requirements 10.2, 10.3**
 */

import * as fc from "fast-check";
import { describe, expect,it } from "vitest";

import {
  eventHasProtocolLink,
  filterEventsByType,
  getUniqueEventTypes,
} from "@/lib/api/hooks/use-events";
import type { Event } from "@/lib/api/types";

// Arbitrary generator for event IDs
const eventIdArbitrary = fc.nat({ min: 1, max: 100000 });

// Arbitrary generator for event types
const eventTypeArbitrary = fc.constantFrom(
  "protocol_started",
  "protocol_completed",
  "protocol_failed",
  "step_started",
  "step_completed",
  "step_failed",
  "agent_assigned",
  "clarification_requested",
  "policy_violation",
  "system_event"
);

// Arbitrary generator for event categories
const eventCategoryArbitrary = fc.option(
  fc.constantFrom("protocol", "step", "agent", "system", "policy"),
  { nil: null }
);

// Arbitrary generator for protocol_run_id (can be null or a number)
const protocolRunIdArbitrary = fc.option(fc.nat({ min: 1, max: 10000 }), { nil: null });

// Arbitrary generator for project_id (can be null or a number)
const projectIdArbitrary = fc.option(fc.nat({ min: 1, max: 1000 }), { nil: undefined });

// Arbitrary generator for step_run_id (can be null or a number)
const stepRunIdArbitrary = fc.option(fc.nat({ min: 1, max: 50000 }), { nil: null });

// Arbitrary generator for a valid Event
const eventArbitrary: fc.Arbitrary<Event> = fc.record({
  id: eventIdArbitrary,
  protocol_run_id: protocolRunIdArbitrary,
  step_run_id: stepRunIdArbitrary,
  event_type: eventTypeArbitrary,
  message: fc.string({ minLength: 1, maxLength: 200 }),
  metadata: fc.option(fc.dictionary(fc.string({ minLength: 1, maxLength: 20 }), fc.string()), {
    nil: null,
  }),
  event_category: eventCategoryArbitrary,
  created_at: fc.constant(new Date().toISOString()),
  protocol_name: fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: undefined }),
  project_id: projectIdArbitrary,
  project_name: fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: undefined }),
});

// Arbitrary generator for an array of events
const eventsArrayArbitrary = fc.array(eventArbitrary, { minLength: 0, maxLength: 50 });

// Arbitrary generator for event type filter (including "all")
const eventTypeFilterArbitrary = fc.oneof(fc.constant("all"), eventTypeArbitrary);

describe("Event Feed Property Tests", () => {
  /**
   * Property 13: Event feed filtering consistency
   * For any event type filter, all displayed events SHALL have a type matching the filter value.
   * **Validates: Requirements 10.2**
   */
  describe("Property 13: Event feed filtering consistency", () => {
    it('should return all events when filter is "all"', () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, (events) => {
          const filtered = filterEventsByType(events, "all");

          // When filter is "all", all events should be returned
          expect(filtered.length).toBe(events.length);
          expect(filtered).toEqual(events);
        }),
        { numRuns: 100 }
      );
    });

    it("should return all events when filter is empty string", () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, (events) => {
          const filtered = filterEventsByType(events, "");

          // When filter is empty, all events should be returned
          expect(filtered.length).toBe(events.length);
          expect(filtered).toEqual(events);
        }),
        { numRuns: 100 }
      );
    });

    it("should only return events matching the filter type", () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, eventTypeArbitrary, (events, filterType) => {
          const filtered = filterEventsByType(events, filterType);

          // All filtered events should have the matching event_type
          for (const event of filtered) {
            expect(event.event_type).toBe(filterType);
          }
        }),
        { numRuns: 100 }
      );
    });

    it("should return subset of original events when filtering", () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, eventTypeFilterArbitrary, (events, filterType) => {
          const filtered = filterEventsByType(events, filterType);

          // Filtered result should never be larger than original
          expect(filtered.length).toBeLessThanOrEqual(events.length);
        }),
        { numRuns: 100 }
      );
    });

    it("should preserve event order when filtering", () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, eventTypeArbitrary, (events, filterType) => {
          const filtered = filterEventsByType(events, filterType);

          // Check that filtered events maintain their relative order
          const filteredIds = filtered.map((e) => e.id);
          const originalFilteredIds = events
            .filter((e) => e.event_type === filterType)
            .map((e) => e.id);

          expect(filteredIds).toEqual(originalFilteredIds);
        }),
        { numRuns: 100 }
      );
    });

    it("should return empty array when no events match filter", () => {
      fc.assert(
        fc.property(
          fc
            .array(
              fc.record({
                ...eventArbitrary.generator,
                event_type: fc.constant("protocol_started"),
              } as unknown as fc.RecordConstraints<Event>),
              { minLength: 1, maxLength: 10 }
            )
            .map((arr) => arr.map((e) => ({ ...e, event_type: "protocol_started" }) as Event)),
          (events) => {
            // Filter for a type that doesn't exist in the array
            const filtered = filterEventsByType(events, "step_failed");

            // Should return empty array when no matches
            expect(filtered.length).toBe(0);
          }
        ),
        { numRuns: 100 }
      );
    });

    it("should be idempotent - filtering twice gives same result", () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, eventTypeFilterArbitrary, (events, filterType) => {
          const filtered1 = filterEventsByType(events, filterType);
          const filtered2 = filterEventsByType(filtered1, filterType);

          // Filtering twice should give the same result
          expect(filtered2).toEqual(filtered1);
        }),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Property 14: Event feed protocol links
   * For any event with a non-null protocol_run_id, the rendered event SHALL include
   * a clickable link to that protocol.
   * **Validates: Requirements 10.3**
   */
  describe("Property 14: Event feed protocol links", () => {
    it("should return true for events with valid protocol_run_id", () => {
      fc.assert(
        fc.property(fc.nat({ min: 1, max: 10000 }), (protocolId) => {
          const event: Event = {
            id: 1,
            protocol_run_id: protocolId,
            step_run_id: null,
            event_type: "protocol_started",
            message: "Test event",
            metadata: null,
            created_at: new Date().toISOString(),
          };

          expect(eventHasProtocolLink(event)).toBe(true);
        }),
        { numRuns: 100 }
      );
    });

    it("should return false for events with null protocol_run_id", () => {
      fc.assert(
        fc.property(eventIdArbitrary, (eventId) => {
          const event: Event = {
            id: eventId,
            protocol_run_id: null,
            step_run_id: null,
            event_type: "system_event",
            message: "Test event",
            metadata: null,
            created_at: new Date().toISOString(),
          };

          expect(eventHasProtocolLink(event)).toBe(false);
        }),
        { numRuns: 100 }
      );
    });

    it("should correctly identify protocol links for any event", () => {
      fc.assert(
        fc.property(eventArbitrary, (event) => {
          const hasLink = eventHasProtocolLink(event);

          // hasLink should be true if and only if protocol_run_id is a number
          const expectedHasLink =
            typeof event.protocol_run_id === "number" && event.protocol_run_id !== null;
          expect(hasLink).toBe(expectedHasLink);
        }),
        { numRuns: 100 }
      );
    });

    it("should handle zero protocol_run_id as having a link", () => {
      // Zero is a valid ID in some systems
      const event: Event = {
        id: 1,
        protocol_run_id: 0,
        step_run_id: null,
        event_type: "protocol_started",
        message: "Test event",
        metadata: null,
        created_at: new Date().toISOString(),
      };

      // Zero is typeof number, so it should have a link
      expect(eventHasProtocolLink(event)).toBe(true);
    });
  });

  /**
   * Additional property tests for getUniqueEventTypes utility
   */
  describe("getUniqueEventTypes utility", () => {
    it("should return unique event types", () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, (events) => {
          const types = getUniqueEventTypes(events);

          // All types should be unique
          const uniqueSet = new Set(types);
          expect(types.length).toBe(uniqueSet.size);
        }),
        { numRuns: 100 }
      );
    });

    it("should return sorted event types", () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, (events) => {
          const types = getUniqueEventTypes(events);

          // Types should be sorted
          const sorted = [...types].sort();
          expect(types).toEqual(sorted);
        }),
        { numRuns: 100 }
      );
    });

    it("should only include event types present in the events", () => {
      fc.assert(
        fc.property(eventsArrayArbitrary, (events) => {
          const types = getUniqueEventTypes(events);
          const eventTypesInArray = new Set(events.map((e) => e.event_type).filter(Boolean));

          // All returned types should be in the original events
          for (const type of types) {
            expect(eventTypesInArray.has(type)).toBe(true);
          }

          // All event types from events should be in the result
          for (const type of eventTypesInArray) {
            expect(types).toContain(type);
          }
        }),
        { numRuns: 100 }
      );
    });

    it("should return empty array for empty events", () => {
      const types = getUniqueEventTypes([]);
      expect(types).toEqual([]);
    });
  });
});
