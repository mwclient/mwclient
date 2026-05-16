"""WikiBase Entities and related objects."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


class Entity:
    """Wikibase Entity, either Item or Property.

    This class should not be implemented directly,
    It is meant to be abstract for Item and Property.

    Attributes:
        site: reference to a WikiBaseSite
        entity: Q/P number of the entity.
        descriptions: dictionary containing description per language
        labels: dictionary containing labels per language
    """

    def __init__(self, site: Any, normalized_entity: str) -> None:
        """Common part of constructor for Item and Property."""
        self.site = site
        self.entity = normalized_entity
        self._descriptions: Optional[dict[str, str]] = None
        self._labels: Optional[dict[str, str]] = None
        self._itemclaims: Optional[list[Claim]] = None

    def setinfofromwbgetentities(self, result: dict[str, Any]) -> None:
        """Set descriptions, labels and claims from wbgetentities result."""
        self._descriptions = {}
        for language in result['descriptions']:
            lang = result['descriptions'][language]['language']
            value = result['descriptions'][language]['value']
            self._descriptions[lang] = value
        self._labels = {}
        for language in result['labels']:
            lang = result['labels'][language]['language']
            value = result['labels'][language]['value']
            self._labels[lang] = value
        if self._itemclaims is None:
            self._itemclaims = []
            for prop in result['claims']:
                for claim in result['claims'][prop]:
                    mainsnak = claim['mainsnak']
                    self._itemclaims.append(Claim.fromsnak(self.site, mainsnak))

    @property
    def labels(self) -> dict[str, str]:
        """Labels dictionary per language"""
        if self._labels is None:
            entities = self.site.api('wbgetentities', ids=self.entity)
            result = entities['entities'][self.entity]
            self.setinfofromwbgetentities(result)
        assert self._labels is not None
        return self._labels

    @property
    def descriptions(self) -> dict[str, str]:
        """Descriptions dictionary per language"""
        if self._descriptions is None:
            entities = self.site.api('wbgetentities', ids=self.entity)
            result = entities['entities'][self.entity]
            self.setinfofromwbgetentities(result)
        assert self._descriptions is not None
        return self._descriptions

    def claims(self, prop: Optional[list[str]] = None) -> list[Claim]:
        """Claims about an Entity.

        API Doc: https://www.mediawiki.org/wiki/Wikibase/API/en#wbgetclaims

        Args:
            prop: list of property e.g. ['P238', 'P239']
        """
        if self._itemclaims is None:
            self._itemclaims = []
            info = self.site.api('wbgetclaims', entity=self.entity)['claims']
            for propid in info:
                for claim in info[propid]:
                    mainsnak = claim['mainsnak']
                    self._itemclaims.append(Claim.fromsnak(self.site, mainsnak))
        if prop is None:
            return self._itemclaims
        return [claim for claim in self._itemclaims if claim.prop in prop]


class Item(Entity):
    """Wikibase Item.

    Attributes:
        site: reference to a WikiBaseSite
        entity: Q number of the entity.
        sitelinks: dictionary containing sitelinks per wiki
        descriptions: dictionary containing description per language
        labels: dictionary containing labels per language
    """

    def __init__(self, site: Any, entity: str) -> None:
        """Constructor.

        Args:
            site: reference to a WikiBaseSite
            entity: Q number of the entity.
        """
        super().__init__(site, 'Q' + entity.upper().lstrip('Q'))
        self._sitelinks: Optional[dict[str, dict[str, Any]]] = None

    def setinfofromwbgetentities(self, result: dict[str, Any]) -> None:
        """Set sitelinks, descriptions, labels, claims from wbgetentities."""
        super().setinfofromwbgetentities(result)
        self._sitelinks = {}
        for wiki in result['sitelinks']:
            site = result['sitelinks'][wiki]['site']
            title = result['sitelinks'][wiki]['title']
            badges = result['sitelinks'][wiki]['badges']
            self._sitelinks[site] = {'title': title, 'badges': badges}

    @property
    def sitelinks(self) -> dict[str, dict[str, Any]]:
        """Sitelinks dictionary with title, and badges per site."""
        if self._sitelinks is None:
            entities = self.site.api('wbgetentities', ids=self.entity)
            result = entities['entities'][self.entity]
            self.setinfofromwbgetentities(result)
        assert self._sitelinks is not None
        return self._sitelinks

    def __repr__(self) -> str:
        """Item representation."""
        return "<Item object %s (%s)>" % (self.entity, self.site.host)


class Property(Entity):
    """Wikibase Property."""

    def __init__(self, site: Any, entity: str) -> None:
        """Constructor.

        Args:
            site: reference to a WikiBaseSite
            entity: P number of the entity.
        """
        super().__init__(site, 'P' + entity.upper().lstrip('P'))

    def __repr__(self) -> str:
        """Property representation."""
        return "<Property object %s (%s)>" % (self.entity, self.site.host)


class Claim:
    """Claim

    Attributes:
        prop: property id.
        snak: snak with all values return in mainsnak from API call.
        snaktype: 'value', 'somevalue' or 'novalue'
        datatype: datatype ('wikibase-item', 'string', etc.)
        raw_value: content of snak['datavalue']['value'] if snaktype is
            'value', None otherwise.
        value: typed content of snak['datavalue']['value']
    """

    def __init__(
        self,
        site: Any,
        prop: str,
        datatype: str,
        snaktype: str,
        raw_value: Any = None,
        snak: Optional[dict[str, Any]] = None,
    ) -> None:
        """Constructor"""
        self.site = site
        self.prop = prop
        self.datatype = datatype
        self.raw_value = raw_value
        self.snaktype = snaktype
        self.snak = snak

    @classmethod
    def fromsnak(cls, site: Any, snak: dict[str, Any]) -> Claim:
        """Claim from snak dictionary.

        Args:
            site: site
            snak: snak dictionary
        """
        snakvalue = None
        if snak['snaktype'] == 'value':
            snakvalue = snak['datavalue']['value']
        return cls(
            site,
            snak['property'],
            snak['datatype'],
            snak['snaktype'],
            raw_value=snakvalue,
            snak=snak,
        )

    def __repr__(self) -> str:
        """Representation."""
        return "<Claim object %s [%s]>" % (self.prop, self.datatype)

    @property
    def value(self) -> Any:
        if self.datatype == 'string':
            return self.raw_value
        elif self.datatype == 'monolingualtext':
            return MonolingualText(**self.raw_value)
        elif self.datatype == 'commonsMedia':
            return self.raw_value
        elif self.datatype == 'external-id':
            return self.raw_value
        elif self.datatype == 'wikibase-item':
            return Item(self.site, str(self.raw_value['numeric-id']))
        elif self.datatype == 'wikibase-property':
            return Property(self.site, str(self.raw_value['numeric-id']))
        elif self.datatype == 'globe-coordinate':
            return GlobeCoordinate(**self.raw_value)
        elif self.datatype == 'time':
            return TimeData(**self.raw_value)
        elif self.datatype == 'quantity':
            return Quantity(**self.raw_value)
        else:
            return self.raw_value


@dataclass
class GlobeCoordinate:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    precision: Optional[float] = None
    globe: Optional[str] = None


@dataclass
class TimeData:
    time: Optional[str] = None
    timezone: Optional[int] = None
    before: Optional[int] = None
    after: Optional[int] = None
    precision: Optional[int] = None
    calendarmodel: Optional[str] = None


@dataclass
class Quantity:
    amount: Optional[str] = None
    unit: Optional[str] = None
    upperBound: Optional[str] = None
    lowerBound: Optional[str] = None


@dataclass
class MonolingualText:
    text: Optional[str] = None
    language: Optional[str] = None
