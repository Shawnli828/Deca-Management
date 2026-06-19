'use client';

import { publishCheckPeople, sortPublishCheckAssignments, type PublishAssignmentSort } from '@/lib/publishCheckFormatters';
import type { Product, PublishCheckAssignment, PublishCheckState } from '@/lib/types';
import {
  AssignmentForm,
  AssignmentTable
} from './PublishCheckAssignments';
import {
  PublishCheckHero,
  PublishCheckWindow
} from './PublishCheckParts';
import {
  PublishResultPanel
} from './PublishCheckResults';
import { FormEvent, useEffect, useMemo, useState } from 'react';

export function PublishCheckBoard({
  products,
  state,
  running,
  sendingReminder,
  onSave,
  onRun,
  onSendReminder
}: {
  products: Product[];
  state: PublishCheckState;
  running: boolean;
  sendingReminder: boolean;
  onSave: (state: PublishCheckState) => Promise<void>;
  onRun: () => Promise<void>;
  onSendReminder: () => Promise<void>;
}) {
  const people = useMemo(() => {
    return publishCheckPeople(state.assignments);
  }, [state.assignments]);
  const [personName, setPersonName] = useState(people[0]?.name || '');
  const [productId, setProductId] = useState(products[0]?.id || '');
  const selectedProduct = products.find(product => product.id === productId) || products[0];
  const [countryId, setCountryId] = useState(selectedProduct?.countries?.[0]?.id || '');
  const [assignmentSort, setAssignmentSort] = useState<PublishAssignmentSort>('person');
  const [expandedResultCards, setExpandedResultCards] = useState<Record<string, boolean>>({});
  const result = state.last_result;

  const peopleById = useMemo(() => new Map(people.map(person => [person.id, person])), [people]);
  const sortedAssignments = useMemo(() => {
    return sortPublishCheckAssignments(state.assignments, products, assignmentSort);
  }, [assignmentSort, products, state.assignments]);

  useEffect(() => {
    if (!personName && people[0]?.name) setPersonName(people[0].name);
    if (!productId && products[0]?.id) {
      setProductId(products[0].id);
      setCountryId(products[0].countries?.[0]?.id || '');
    }
  }, [personName, productId, products, people]);

  function addAssignment(event: FormEvent) {
    event.preventDefault();
    const product = products.find(item => item.id === productId);
    const country = product?.countries?.find(item => item.id === countryId);
    const cleanName = personName.trim();
    if (!product || !country || !cleanName) return;
    const personId = cleanName.toLowerCase().replace(/\s+/g, '-');

    const exists = state.assignments.some(item => item.person_id === personId && item.product_id === product.id && item.country_id === country.id);
    if (exists) return;

    const assignment: PublishCheckAssignment = {
      id: crypto.randomUUID(),
      person_id: personId,
      person_name: cleanName,
      product_id: product.id,
      country_id: country.id
    };
    onSave({ ...state, assignments: [...state.assignments, assignment] });
  }

  function removeAssignment(id: string) {
    onSave({ ...state, assignments: state.assignments.filter(item => item.id !== id) });
  }

  function changeProduct(nextProductId: string) {
    setProductId(nextProductId);
    const product = products.find(item => item.id === nextProductId);
    setCountryId(product?.countries?.[0]?.id || '');
  }

  return (
    <section className="publish-check-board">
      <PublishCheckHero running={running} onRun={onRun} />
      <PublishCheckWindow result={result} />

      <section className="publish-check-panel">
        <div className="publish-check-panel-head">
          <div>
            <h3>负责范围</h3>
            <p>配置每个人负责的产品和国家/地区。</p>
          </div>
        </div>
        <AssignmentForm
          people={people}
          products={products}
          selectedProduct={selectedProduct}
          personName={personName}
          productId={productId}
          countryId={countryId}
          onPersonNameChange={setPersonName}
          onProductChange={changeProduct}
          onCountryChange={setCountryId}
          onSubmit={addAssignment}
        />
        <AssignmentTable
          assignments={sortedAssignments}
          products={products}
          peopleById={peopleById}
          assignmentSort={assignmentSort}
          onSortChange={setAssignmentSort}
          onRemove={removeAssignment}
        />
      </section>

      <PublishResultPanel
        result={result}
        sendingReminder={sendingReminder}
        expandedResultCards={expandedResultCards}
        onSendReminder={onSendReminder}
        onToggleResultCard={id => setExpandedResultCards(prev => ({ ...prev, [id]: !prev[id] }))}
      />
    </section>
  );
}
